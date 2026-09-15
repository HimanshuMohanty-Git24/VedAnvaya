# Corpus / Structural Metadata Audit

Agent 2 of the Post-V1 Data Completeness Campaign. Every figure below was measured
against the live graph on the date shown, with read-only Cypher. Nothing was taken from
a previous report; where a previous report and this one differ, both numbers appear and
the query that produced this one is given.

- Measured: 2026-09-15
- Branch: `phase-data-completeness-v2`
- Access: `MATCH` / `RETURN` only, `bolt://localhost:7687`, database `neo4j`
- Denominators (confirmed at baseline, reused not re-derived): RV 10,552 / SV 1,844 /
  YV 1,975 / AV 5,839 = 20,210 `:Mantra`
- Artifacts: `data/staging/corpus_audit/coverage_matrix.json`,
  `data/staging/corpus_audit/per_passage_coverage.csv` (20,210 rows, 35 columns)

---

## 1. What the vocabulary actually is

`db.labels()` and `db.relationshipTypes()` were enumerated in full before any dimension
was counted, and `keys(n)` sampled on every label used below. Four things that a schema
reading would get wrong:

1. **Sanskrit text is not a property of a mantra.** `:Mantra` carries exactly fifteen
   properties and none of them is the text. Text lives only on `:TextVersion`
   (44,276 nodes) reached by `HAS_TEXT_VERSION`, in `text_nfc`.
2. **`HAS_FORMULA` is not a passage-level relationship.** It runs
   `FormulaFamily -> Formula` (2,037 edges) and never leaves a `:Mantra`. The
   passage-level formula relation is `USES_FORMULA` alone.
3. **`:Source` has zero relationships.** Provenance is a bare string join from
   `TextVersion.source_id` / `Translation.source_id` to `Source.source_id`.
4. **`:SourceArtifact` is declared and empty.** Zero nodes.

Accent, likewise, was measured from the characters rather than read off
`TextVersion.accented` — see §5.

---

## 2. The coverage matrix

Numerator is distinct mantras; denominator is that Veda's canonical total. The
classification column is the one that decides how a shortfall should be read, and §3
defines it.

| Dimension | Class | RV / 10,552 | SV / 1,844 | YV / 1,975 | AV / 5,839 |
|---|---|---|---|---|---|
| Sanskrit text, non-empty | LOGICALLY EXPECTED | 10,552 (100.0%) | 1,844 (100.0%) | 1,975 (100.0%) | 5,839 (100.0%) |
| Sanskrit at `PRIMARY_TEXT` role | LOGICALLY EXPECTED | 10,552 (100.0%) | 1,844 (100.0%) | **0 (0.0%)** | 5,839 (100.0%) |
| Accent (measured in the string) | RECENSION CONDITIONAL | 10,552 (100.0%) | 0 (0.0%) | 1,974 (99.9%) | 5,839 (100.0%) |
| Pada segmentation | RECENSION CONDITIONAL | **0 (0.0%)** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Translation, any alignment | LOGICALLY EXPECTED | 10,502 (99.5%) | 0 (0.0%) | 1,903 (96.4%) | 4,878 (83.5%) |
| Translation, mantra-aligned | LOGICALLY EXPECTED | 10,344 (98.0%) | 0 (0.0%) | 1,903 (96.4%) | 4,878 (83.5%) |
| Rishi (`HAS_RISHI`) | TRADITION EXPECTED | 10,534 (99.8%) | 0 (0.0%) | 1,960 (99.2%) | 4,542 (77.8%) |
| Devata (`HAS_DEVATA` strictly) | TRADITION EXPECTED | 10,552 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Devata ascription (`HAS_DEVATA_ASCRIPTION`) | TRADITION EXPECTED | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 4,160 (71.2%) |
| **Dedication recorded by either mechanism** | TRADITION EXPECTED | 10,552 (100.0%) | 0 (0.0%) | 0 (0.0%) | **4,160 (71.2%)** |
| Chandas | TRADITION EXPECTED | 10,518 (99.7%) | 0 (0.0%) | 0 (0.0%) | 4,082 (69.9%) |
| Structural hierarchy to Work root | LOGICALLY EXPECTED | 10,552 (100.0%) | 1,844 (100.0%) | 1,975 (100.0%) | 5,839 (100.0%) |
| Provenance: a `source_id` is present | LOGICALLY EXPECTED | 10,552 (100.0%) | 1,844 (100.0%) | 1,975 (100.0%) | 5,839 (100.0%) |
| Provenance: every `source_id` resolves | LOGICALLY EXPECTED | 10,552 (100.0%) | 1,844 (100.0%) | **72 (3.6%)** | 5,839 (100.0%) |
| Audio recording | OPTIONAL, ASSESSED | 10,402 (98.6%) | 0 (0.0%) | 1,752 (88.7%) | 4,680 (80.2%) |
| Lemma / morphology | INHERENTLY OPTIONAL | 6,560 (62.2%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| Entity mentions | INHERENTLY OPTIONAL | 8,143 (77.2%) | 1,306 (70.8%) | 1,358 (68.8%) | 4,292 (73.5%) |
| `MENTIONS_DEVATA` | INHERENTLY OPTIONAL | 7,099 (67.3%) | 1,035 (56.1%) | 1,167 (59.1%) | 2,616 (44.8%) |
| Formula membership (`USES_FORMULA`) | INHERENTLY OPTIONAL | 5,103 (48.4%) | 1,311 (71.1%) | 1,214 (61.5%) | 2,946 (50.5%) |
| Parallel / reuse (undirected) | INHERENTLY OPTIONAL | 2,850 (27.0%) | 1,677 (90.9%) | 687 (34.8%) | 1,332 (22.8%) |
| Semantic assertion | INHERENTLY OPTIONAL | 2,542 (24.1%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

The YV provenance figure is not a coincidence: 1,975 − 1,903 = 72. The only Yajurvedic
mantras whose provenance resolves are the 72 that have no translation at all. See
CORPUS_D02.

### Status, per Veda per dimension

Never read a zero above without this table. `OBSERVED` = a positive measured count.

| Dimension | RV | SV | YV | AV |
|---|---|---|---|---|
| Sanskrit text | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| `PRIMARY_TEXT` role | OBSERVED | OBSERVED | **VERIFIED ZERO** | OBSERVED |
| Accent | OBSERVED | **VERIFIED ZERO** | OBSERVED | OBSERVED |
| Pada segmentation | **NOT ASSESSED** | NOT APPLICABLE | NOT APPLICABLE | NOT APPLICABLE |
| Translation | OBSERVED | **NOT ASSESSED** | OBSERVED | OBSERVED |
| Rishi | OBSERVED | **NOT ASSESSED** | OBSERVED | OBSERVED |
| `HAS_DEVATA` | OBSERVED | NOT ASSESSED | NOT ASSESSED | **NOT ASSESSED** |
| `HAS_DEVATA_ASCRIPTION` | NOT APPLICABLE | NOT ASSESSED | NOT ASSESSED | OBSERVED |
| Chandas | OBSERVED | NOT ASSESSED | NOT ASSESSED | OBSERVED |
| Structural hierarchy | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| Provenance | OBSERVED | OBSERVED | OBSERVED (unresolvable) | OBSERVED |
| Audio | OBSERVED | **VERIFIED ZERO** | OBSERVED | OBSERVED |
| Lemma / morphology | OBSERVED | NOT ASSESSED | NOT ASSESSED | NOT ASSESSED |
| Entity mentions | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| `MENTIONS_DEVATA` | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| Formula membership | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| Parallel / reuse | OBSERVED | OBSERVED | OBSERVED | OBSERVED |
| Semantic assertion | OBSERVED | NOT ASSESSED | NOT ASSESSED | NOT ASSESSED |

Only three cells in the whole matrix earn VERIFIED ZERO, and each earns it from evidence
outside the edge count: the Samavedic accent zero from a measured registry record that
corrected an earlier claim plus a zero-mark scan of all 1,844 strings; the Samavedic
audio zero from the enumerated catalog file and its own measured caveat; the Yajurvedic
`PRIMARY_TEXT` zero because all 1,975 layers demonstrably carry a different role.

`HAS_DEVATA` for the Atharvaveda is marked NOT ASSESSED rather than VERIFIED ZERO for a
specific reason: dedication *is* recorded for 4,160 AV mantras, through the other
mechanism. A reader who queries `HAS_DEVATA` alone is told the Atharvaveda has no deity
attribution, and that is false.

---

## 3. Expected versus optional, per dimension

This is the distinction that governs how every number above should be read.

**LOGICALLY EXPECTED — target is 100%, and a shortfall is a gap.**
Sanskrit text; Sanskrit at a primary role; structural hierarchy; source provenance;
translation. A mantra with no text is not a mantra; a mantra that does not resolve to its
Work root is unaddressable; a mantra whose provenance does not resolve cannot be cited.
Translation belongs here rather than with the optional dimensions because a verse in a
released corpus is either translated or it is a gap — there is no sense in which a verse
is "optionally" translatable.

**TRADITION EXPECTED — a shortfall is unfinished ingestion, not a property of the text.**
Rishi, devata, chandas. The Anukramani tradition transmits a seer, a deity and a metre
for the Rigveda and the Atharvaveda, so a missing value is work not yet done. It is a
weaker claim than LOGICALLY EXPECTED because the witness held for a given recension may
simply not print the attribution, and because the Yajurveda's and Samaveda's traditions
differ in what they transmit at verse level at all.

**RECENSION CONDITIONAL — state N/A per Veda, never zero.**
Accent and pada segmentation. Whether either exists depends on the witness. Reporting
"0% padapatha" for the Samaveda as though it were a gap would be inventing a defect; the
Kauthuma arcika witness held here has no padapatha to ingest. The Rigveda is the one
place where the padapatha zero *is* a gap, because a padapatha layer was declared and
never landed (CORPUS_D05).

**INHERENTLY OPTIONAL — no mantra is required to have a positive value.**
Lemma, entity mentions, `MENTIONS_DEVATA`, formula membership, parallel/reuse, semantic
assertion. Not every verse contains a named entity, reuses a formula, or has a textual
parallel somewhere else in the corpus. **For these six, the percentage in §2 is the
`positive` number and there is no `assessed` number to report.** §4 is about why.

**OPTIONAL BUT ASSESSED — the one dimension where both numbers exist.**
Audio. See §6.

---

## 4. Assessed-empty versus never-assessed

**For every inherently optional dimension held inside the graph, the graph cannot
distinguish "assessed and came back empty" from "never assessed."** This is the single
most consequential finding in this audit, and it is a fact about where provenance is
written rather than a limit of this measurement.

The pipelines record their work thoroughly — `run_id`, `pipeline_version`, `method`,
`execution_version`, `prompt_version`, `model`, `score`, `trust`, `state`, `evidence`,
`evidence_count` — but they record it **on the thing they produced**: on the dimension
relationship itself, or on the `:SemanticAssertion` / `:Formula` / `:FormulaFamily` node.
Nothing is ever written on the `:Mantra` that was examined. A `:Mantra` carries exactly
fifteen properties (`canonical_citation`, `canonical_key`, `canonical_urn`,
`display_label`, `display_type`, `entity_id`, `entity_type`, `hierarchy`,
`native_labels`, `parent_key`, `sequence_in_parent`, `status`, `structural_path`, `veda`,
`work_id`) and not one of them records an enrichment run. There is no assessed-set node.
The 1,072 `:DerivedMetric` nodes hold aggregate distributions by Work, by devata and by
action; none records an examined population for a dimension.

So a mantra with no `MENTIONS_ENTITY` edge is indistinguishable from a mantra the entity
detector never read. The absence cannot be typed in the row — only inferred from the
pattern of absence across a Veda.

One thing *is* recoverable. Because the surviving edges carry `run_id`, the set of Vedas
a run touched can be reconstructed even though the set of mantras it examined cannot.
That yields a population-level answer, not a per-passage one:

| Dimension | Resolution | What is recorded |
|---|---|---|
| Entity mentions | POPULATION-LEVEL ONLY | One run, `domain-mentions:59550575a4870e52`, emitted edges in all four Vedas. |
| `MENTIONS_DEVATA` | POPULATION-LEVEL ONLY | One run, `theonym-mentions:b3f932967d1e334f`, all four Vedas. |
| Formula membership | POPULATION-LEVEL ONLY | One run, `formulas:5f3a96b6a04a2557`, all four Vedas. |
| Parallel / reuse | POPULATION-LEVEL ONLY, **and incomplete** | One run, `crossveda-parallels:5bf3c9ce73209098`, emitted subjects in RV, SV and AV only. Whether the Yajurveda was assessed as a subject and rejected, or never assessed as one, **is not recorded**. |
| Semantic assertion | POPULATION-LEVEL ONLY, **Rigveda only** | Two runs, both RV: `agentive-assertions:6cbe63b24f5023cf` (2,228 mantras, `agentive-morphology-v1`) and `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1` (398 mantras, `rigveda-semantic-execution-v3.2`). SV, YV and AV are named by no run at all. |
| Lemma / morphology | **NOT RECORDED AT ALL** | `MENTIONS_LEMMA` carries no `run_id`, no `pipeline_version` and no `method` — only `provenance_class='DETERMINISTIC_DERIVED'`. Even the population-level inference available for the other five is unavailable. The RV 6,560 and the SV/YV/AV zeros are equally unexplained. |
| Chandas | NOT RECORDED as a population | `HAS_CHANDAS` carries `build_pass`, `source_id`, `scope_origin`, `confidence` — how a positive was derived, not who was examined. Nothing records metre having been sought for SV or YV. |
| Rishi, devata | NOT RECORDED as a population | As chandas. |
| Audio | **FULLY RESOLVED** | The only one. §6. |

### Instruction for later agents

Treat every zero in an INHERENTLY OPTIONAL column of `per_passage_coverage.csv` as
**UNKNOWN**, never as a negative finding, unless the status table in §2 says otherwise.
Lemma is the worst case: do not report "the Atharvaveda has no lemmas" — report "no
lemma edge exists for any Atharvavedic mantra and nothing records whether the lemmatiser
ever read one."

If the campaign wants assessed-versus-positive to become answerable per passage, the
assessed population has to be written down **at assessment time** — a marker per
(mantra, dimension, run). It cannot be recovered after the fact from the graph as it
stands.

### One thing that is clean

Every mantra-level dimension edge carrying a `state` property is `state='ACCEPTED'`, so
for all fifteen dimensions "has an edge" does equal "positive". `CANDIDATE` edges exist,
but only on the ritual and semantic layers (`INVOKES`, `REQUESTS`, `PRAISES`,
`DESCRIBES`, `HAS_THEME` and similar), which are outside these dimensions. No dimension
count above is inflated by unreviewed candidates.

---

## 5. Where accent is actually stored

All three of the candidate answers are partly right, and only one is load-bearing.

**Accent is stored inline, in `TextVersion.text_nfc`.** `TextVersion.accented` is a
declared boolean describing the layer, and accent is *also* the axis along which a
recension's several `TextVersion` layers differ — the accented and unaccented readings of
the Atharvaveda are two separate `TextVersion` nodes hanging off the same mantra. So the
flag exists, the separate-version story is real, but the marks themselves are in the
string and that is what was counted.

The notation is not uniform across the corpus, which matters for anyone writing an
accent-aware query:

| Layer | Marks present |
|---|---|
| RV `PRIMARY_TEXT` (GRETIL) | U+0331 anudatta (101,175) and U+030D svarita (74,801); udatta unmarked |
| RV `PARALLEL_TEXT` (VedaWeb) | U+0301 udatta on a vowel (128,482), U+0300 (2,080) — a different convention for the same verses |
| AV `PRIMARY_TEXT` (GRETIL) | U+0301 on a vowel (68,834), U+0300 (1,279) |
| YV `EXTRACTED_FROM_CONTAINER` (Wikisource) | Devanagari U+0952 anudatta (24,329), U+0951 udatta (17,204), one U+1CD4 |
| SV `PRIMARY_TEXT` (Wikisource) | none |

Flag and string agree on 44,275 of 44,276 `TextVersion` nodes; the one exception is
CORPUS_D09.

### Two traps that invent coverage, and were avoided

**U+0301 is both the udatta and the palatal sibilant.** In IAST, `ś` is `s` + U+0301.
Counting U+0301 by codepoint reports all 5,839 of the Atharvaveda's deliberately
unaccented `PARALLEL_TEXT` versions as accented, on 6,789 stray sibilant marks. The
accent test must require a **vowel** base character.

**A codepoint range over the Vedic Extensions block is not a tone-mark test.** U+1CEA and
U+1CEC are *anusvara* signs and U+A8F3 a *candrabindu*: nasalisation, not accent. A
range test reported 780 accented verses in the Yajurvedic `PARALLEL_TEXT` layer that
`data/registry/text_versions.yaml` correctly calls unaccented. Restricting the class to
codepoints whose Unicode **name** contains TONE, SVARITA, UDATTA or ANUDATTA gives the
correct answer: zero. The registry was right and the broad character class was wrong.

---

## 6. Where audio actually lives

**Not in the graph.** No audio label, node, relationship or property exists; both the
label and relationship-type vocabularies were enumerated in full to confirm it.

The authoritative store is **`data/product/audio_catalog.jsonl`** — a committed
16,834-line JSONL sidecar, 23,563,875 bytes, one record per verse, keyed by `scope_key`
which is the mantra's `canonical_key`. No binary media is held: `data/audio/cache`
contains only `.gitkeep`, and every record is `playback_mode: PROXIED_STREAM` with
`local_cache_path: null`. It is served through `/api/v1/audio/stats`,
`/api/v1/audio/{audio_id}`, `/api/v1/audio/{audio_id}/stream`,
`/api/v1/passages/{key}/audio` and `/api/v1/works/{work_id}/audio`.

`AudioCatalog.resolve` walks *up* the colon-delimited key and returns `levels_above`, so
a container's recording is reported as a container's recording rather than copied onto
each of its mantras. All 16,834 present records are `scope_type: MANTRA` at
`levels_above: 0`.

| Veda | Mapped | Total | Gap |
|---|---|---|---|
| RV | 10,402 | 10,552 | 150 |
| SV | 0 | 1,844 | 1,844 |
| YV | 1,752 | 1,975 | 223 |
| AV | 4,680 | 5,839 | 1,159 |
| **Total** | **16,834** | **20,210** | **3,376** |

All 16,834 `scope_key` values are distinct and every one resolves to a real `:Mantra`
`canonical_key` — zero dangling.

**Audio is the one optional dimension where "assessed" is knowable**, precisely because
the catalog is an enumerated file rather than an edge that either exists or does not. The
Samavedic zero is therefore a **VERIFIED ZERO** — no Samavedic recording is catalogued by
the selected source, and `/api/v1/audio/stats` carries that as a measured caveat — and
not a NOT ASSESSED.

---

## 7. Structural defects

### CORPUS_D01 — HIGH — the Atharvavedic search layer deletes letters, not just accents

The `SEARCH_DERIVATIVE` layer drops the **base letter** of any grapheme written as base
plus a combining-below mark, instead of dropping only the mark. **5,134 of 5,839 AV
mantras (87.94%)** have a derivative missing at least one base letter that is present in
the `PRIMARY_TEXT`: 11,582 lost an `m` (anusvara, written `m` + U+0323) and 5,139 lost an
`r` (vocalic ṛ, written `r` + U+0325).

```
AVS 1.2.2  primary    jyā̀ke pári ṇo namā́śmānaṃ tanvàṃ kr̥dhi
           derivative jyāke pari ṇo namāśmāna tanva kdhi
AVS 1.2.3  primary    vr̥kṣáṃ yád gā́vaḥ pariṣasvajānā́ anusphuráṃ
           derivative vkṣa yad gāvaḥ pariṣasvajānā anusphura
```

Precomposed characters (`ṣ` U+1E63, `ḍ` U+1E0D, `ḥ` U+1E25, `ṇ` U+1E47) survive, because
in NFC they are single codepoints — which is why the corruption is invisible to a
spot-check that happens to land on a verse without ṛ or ṃ.

**This is live.** `search_service.py` reads `text_role = 'SEARCH_DERIVATIVE'` at lines
269, 494 and 747. Probed against the running API:
`/api/v1/search?q=kr̥dhi&veda=AV` returns **0 passages** although AVS 1.2.2 contains the
word; `q=namāśmānaṃ` likewise returns 0. Since anusvara and vocalic ṛ are pervasive in
Vedic vocabulary, most Atharvavedic verses are unfindable by most of their own words.

Measured by a per-mantra NFD base-letter multiset diff of `PRIMARY_TEXT` against
`SEARCH_DERIVATIVE`. Column `search_derivative_intact` in the CSV; `-1` means the
recension has no derivative layer at all — the Atharvaveda is the only one that does, so
this is an AV-only defect. **Flagged for the search agent.**

### CORPUS_D02 — HIGH — 1,903 Yajurvedic translations point at a source that does not exist

Every Yajurvedic translation carries `source_id = 'SACRED_TEXTS'`, and **no `:Source`
node with that id exists**. Meanwhile
`(:Source {source_id: 'GRIFFITH_WHITE_YAJURVEDA', name: 'The Texts of the White
Yajurveda, Griffith translation'})` does exist and is referenced by nothing. The
translations' own `translator` and `work_edition` fields name exactly that Griffith text.
So the correct Source node is present and orphaned while the pointer dangles.

Measured as the set difference between `source_id` values found on `Translation` and
`TextVersion` and the `source_id` values on `:Source`. This is why
`provenance_source_resolvable` is 72/1,975 for the Yajurveda.

### CORPUS_D03 — MEDIUM — provenance is an unenforced string join

`MATCH (:Source)-[r]-() RETURN count(r)` returns **0**. There is no edge from any
`TextVersion` or `Translation` to its `Source`, and no constraint on the referencing
side. Nothing prevents CORPUS_D02 from recurring, and provenance cannot be traversed in a
graph query — it can only be joined in application code.

### CORPUS_D04 — MEDIUM — the Atharvavedic translation's source_id contradicts its own bibliography

The 4,878 Atharvavedic translations are Whitney and Lanman (Harvard Oriental Series 7–8,
1905) by their own `translator` and `work_edition` fields, but carry
`source_id = 'VEDAWEB'` — a Source whose name in the graph is *"VedaWeb Rigveda public
data"*. `(:Source {source_id: 'WIKISOURCE_WHITNEY_AV', name: 'Atharva-Veda Samhita,
Whitney and Lanman translation'})` exists and is referenced by nothing. Unlike
CORPUS_D02 the pointer resolves, so no automated check catches it; the `source_id` and
the bibliographic fields simply disagree about who published the text. These are also the
only translations in the corpus at `quality_status: UNREVIEWED`.

### CORPUS_D05 — MEDIUM — a committed claim in the graph contradicts the graph

Zero `TextVersion` nodes carry `text_form` or `text_role` of `PADAPATHA`. The full value
space is four combinations — `SAMHITA`/`PRIMARY_TEXT` (18,235),
`SAMHITA`/`PARALLEL_TEXT` (18,227), `SAMHITA`/`SEARCH_DERIVATIVE` (5,839),
`SAMHITA`/`EXTRACTED_FROM_CONTAINER` (1,975) — enumerated rather than grepped for the
expected value.

Yet the RV `:Work` node's `scope` property, which the API serves to readers, asserts:
*"Padapatha and the accented samhitapatha are carried as text versions of these same
mantras, not as separate works."* The accented samhitapatha **is** carried. The padapatha
is not. `data/registry/text_versions.yaml` also declares a VedaWeb layer at `text_form:
PADAPATHA`, `text_role: PADAPATHA` — declared, never ingested.

### CORPUS_D06 — MEDIUM — the Yajurveda has no primary Sanskrit layer

All 1,975 Yajurvedic mantras carry exactly one Sanskrit layer, at
`text_role: EXTRACTED_FROM_CONTAINER`. The `TextRole` enum's own docstring says of that
role: *"must never be selected as primary_sanskrit: doing so would make an interpretive
segmentation canonical."* So either the Yajurveda is being displayed from a role the
model forbids as primary, or it has no primary text. Both readings are problems; the
graph does not settle which one is happening.

### CORPUS_D07 — LOW — parallel edges are directed and asymmetric, so the obvious query lies

| Veda | Has outgoing | Has incoming | Has either |
|---|---|---|---|
| RV | 1,979 | 2,433 | 2,850 |
| SV | 1,667 | 1,675 | 1,677 |
| YV | **0** | 687 | 687 |
| AV | 1,332 | 0 | 1,332 |

No Yajurvedic mantra is ever the **subject** of a parallel edge. `REUSES_TEXT_FROM` is
emitted only from the Samaveda (1,662 subjects); the Rigveda's 1,421 are all incoming. A
directed-outgoing coverage query therefore reports a false zero for the whole Yajurveda
and a false zero for Rigvedic reuse. The CSV columns are **undirected**, which is the
right sense for "is this verse linked to a parallel".

### CORPUS_D08 — LOW — `:SourceArtifact` is declared and empty

Zero nodes. The intended three-part provenance chain — Source, SourceArtifact,
TextVersion — is missing its middle term entirely.

### CORPUS_D09 — LOW — one mantra's accent flag has nothing behind it

`VG:YV:VSM:A20:V015` carries `accented = true` but its string holds no accent mark. Its
only combining signs are U+1CEA and U+1CED — an anusvara sign and the Vedic tiryak sign,
neither a tone mark. 1 of 1,975.

### CORPUS_D10 — INFORMATIONAL — 158 Rigvedic "translations" are hymn-level

158 Rigvedic mantras carry **only** a `Translation` at `alignment_level: HYMN`, not a
per-mantra one. The committed figure "RV translation 10,502" and the Work node's
"10,502 of 10,552 carry a translation (99.5%)" are both literally true — those mantras do
carry a translation — but per-mantra Rigvedic translation coverage is **10,344 / 10,552 =
98.03%**. The CSV separates `translation_any` from `translation_mantra_aligned` so a
later agent cannot conflate them.

### CORPUS_D11 — INFORMATIONAL — identical Sanskrit recurs inside single recensions

By `content_sha256` within one `text_role`: 190 RV mantras (`PRIMARY_TEXT`), 349 SV
(`PRIMARY_TEXT`), 6 YV (`EXTRACTED_FROM_CONTAINER`) and 42 AV (`PRIMARY_TEXT`) share
their text with at least one other mantra of the same recension. The Samavedic cases
concentrate on Aranya-versus-Uttararcika pairs, which is a real feature of the collection
rather than an ingestion fault. Worth noting for the Samaveda specifically given the
recent Aranya-scope clarification. In the Atharvaveda the `SEARCH_DERIVATIVE` layer
collapses far more verses (256) than the `PRIMARY_TEXT` does (42) — a direct consequence
of CORPUS_D01.

---

## 8. Checks that came back clean

| Check | Result |
|---|---|
| Duplicate `canonical_key` among `:Mantra` | 0 |
| Duplicate `canonical_urn` among `:Mantra` | 0 |
| Duplicate `entity_id` among `:Mantra` | 0 |
| Duplicate `canonical_key` among `:Passage` | 0 |
| Mantras not reachable from their Work root (`CONTAINS*1..8`) | 0 — no orphans |
| Mantras with more than one `CONTAINS` parent | 0 |
| Mantras where `veda` and `work_id` disagree | 0 |
| `Mantra.status` value space | `CANONICAL` for all 20,210; no other value exists |
| `TextVersion` with empty or whitespace `text_nfc` | 0 |
| Orphan `TextVersion` / `Translation` | 0 / 0 |
| Non-mantra `Passage` containers holding a translation | 0 |
| Audio `scope_key` values not resolving to a mantra | 0 of 16,834 |
| Mantra-level dimension edges in a non-`ACCEPTED` state | 0 |

`veda` and `work_id` agree exactly, one work per Veda: RV → `VG:WORK:RV:SAK` (10,552),
SV → `VG:WORK:SV:KAU` (1,844), YV → `VG:WORK:YV:VSM` (1,975), AV → `VG:WORK:AV:SAU`
(5,839).

**No placeholder text.** The shortest string is 9 characters and the short ones are
genuine short verses — the AV 5.9 and 19.22–23 *svāhā* formulae, the Kuntapa hymns — not
stubs.

**Hierarchy depth varies legitimately.** Root-to-mantra path length is a uniform 3 for
RV and AV and 2 for YV, but ragged for the Samaveda: 10 mantras at depth 2
(Mahanamnya), 55 at depth 3 (Aranya), 585 at 4 and 1,194 at 5. This is the Samaveda's
actual structure, not a defect — every one of the 1,844 resolves to the Work root.

---

## 9. Disagreements with committed reports

### 9.1 BASELINE.md finding 1 overstates the dedication gap by 4,160 mantras

> **Committed:** "`HAS_DEVATA` exists for the Rigveda only. Dedication is unmodelled for
> SV, YV and AV — three quarters of the recensions, 9,658 mantras."

**Measured:** the `HAS_DEVATA` half is correct. But dedication is **not** unmodelled for
the Atharvaveda: 4,160 of 5,839 AV mantras (71.25%) carry `HAS_DEVATA_ASCRIPTION`, via
4,816 mantra-level edges, plus 505 container-level ascriptions. The genuinely unmodelled
population is SV 1,844 + YV 1,975 + AV 1,679 = **5,498**, not 9,658.

```cypher
MATCH (m:Mantra)-[:HAS_DEVATA_ASCRIPTION]->() RETURN m.veda, count(DISTINCT m)
```

The baseline read one relationship type where the graph uses two. This is the same
type-level attribution hazard already on record: the dedication axis has more than one
writing mechanism, and they partition by Veda.

### 9.2 BASELINE.md finding 5 understates what the Samaveda has

> **Committed:** "Samaveda … is present as Sanskrit text, formula membership and entity
> mentions only."

**Measured:** the Samaveda also carries 1,035 mantras with `MENTIONS_DEVATA` (56.13%) and
1,677 with a parallel or reuse relation (90.94%) — the **highest** parallel coverage of
any Veda, driven by 1,662 `REUSES_TEXT_FROM` subjects. Five layers, not three.

```cypher
MATCH (m:Mantra {veda:'SV'})-[r]-(:Mantra)
WHERE type(r) IN ['EXACT_PARALLEL_OF','NEAR_PARALLEL_OF','VARIANT_OF','REUSES_TEXT_FROM','PARALLEL_TO']
RETURN count(DISTINCT m)
```

### 9.3 The RV Work node's padapatha claim is false

See CORPUS_D05. Half of a committed claim that the API serves to readers.

### 9.4 The registry's Yajurvedic "unaccented" claim is correct — and easy to disprove wrongly

> **Committed** (`data/registry/text_versions.yaml`, Vajasaneyi samhita_block): "UNACCENTED."

**Measured:** correct for the `PARALLEL_TEXT` layer — 1,836 versions, zero tone marks. A
naive codepoint-range scan over the Vedic Extensions block reported 780 of them as
accented. Recorded here because the wrong measurement is the easy one to make, and
because a later agent "correcting" the registry on that basis would be introducing an
error. See §5.

### 9.5 Three committed figures that agree, recorded so nobody re-litigates them

- **BASELINE.md dimension coverage table.** All 32 cells reproduce exactly against the
  live graph: RV 10,502 / 10,534 / 10,552 / 10,518 / 2,542 / 8,143 / 6,560 / 5,103;
  SV 0 / 0 / 0 / 0 / 0 / 1,306 / 0 / 1,311; YV 1,903 / 1,960 / 0 / 0 / 0 / 1,358 / 0 /
  1,214; AV 4,878 / 4,542 / 0 / 4,082 / 0 / 4,292 / 0 / 2,946. The baseline's arithmetic
  is sound; only its two interpretations above diverge.
- **AV Work node: "5,084 seer attributions, every one a sukta label projected downward."**
  Reconciles exactly — 4,542 mantra-level `HAS_RISHI` edges plus 542 container-level =
  5,084, and every mantra-level edge is `knowledge_layer: L2_DETERMINISTIC_DERIVED` with
  `scope_origin: SUKTA_WIDE`. Recorded because a mantra-level query returns 4,542 and
  that looks like a discrepancy until both levels are counted.
- **YV Work node: "every one of this work's 2,240 seer attributions is source-stated."**
  Confirmed — 2,240 edges over 1,960 mantras, all `L1_SOURCE_EXPLICIT` /
  `SINGLE_MANTRA`. The Yajurveda is the only Veda with no derived seer attribution at
  all.

### 9.6 How much attribution is derived rather than source-stated

Not a disagreement, but the figure most likely to be misread as source-stated coverage:

| Veda | Relationship | Source-explicit (L1) | Derived from a container (L2) |
|---|---|---|---|
| RV | `HAS_RISHI` | 467 mantras | 10,067 (sukta-wide) |
| RV | `HAS_DEVATA` | 2,223 | 8,329 (sukta-wide) |
| RV | `HAS_CHANDAS` | 4,242 | 6,276 (sukta-wide) |
| YV | `HAS_RISHI` | 1,960 | 0 |
| AV | `HAS_RISHI` | 0 | 4,542 (sukta-wide) |
| AV | `HAS_CHANDAS` | 1,588 | 3,670 (sukta-wide) |
| AV | `HAS_DEVATA_ASCRIPTION` | 0 | 4,160 (sukta-wide) |

Rigvedic deity attribution is 100% by mantra count but only 21% source-explicit at verse
level. Atharvavedic seer and deity attribution is 0% source-explicit at verse level.

---

## 10. The artifacts

**`data/staging/corpus_audit/per_passage_coverage.csv`** — 20,210 rows, one per canonical
mantra, 35 columns. `1` / `0` booleans throughout, except:

- `audio_recording`: `1` / `0`, resolved against the catalog sidecar.
- `search_derivative_intact`: `-1` where the recension has no derivative layer (RV, SV,
  YV), so it is never confused with `0` = present but corrupted.

The columns are grouped in the header order by class: logically expected, then
recension-conditional, then attribution, then inherently optional, then the two defect
flags. `translation_any` and `translation_mantra_aligned` are separate columns, as are
`devata_has`, `devata_ascription` and their union `devata_any_dedication`. The five
parallel types each have their own column beside the undirected `parallel_any`.

**`data/staging/corpus_audit/coverage_matrix.json`** — per-Veda numerator, denominator,
percentage, status and a measurement note for each of 21 dimension rows, plus the
classification legend, the eleven structural defects, the seven report comparisons, the
fourteen clean checks, the accent-storage analysis and the assessed-versus-positive
resolution table. Every dimension entry carries the `measurement` string describing how
it was counted, so no figure in it is unattributable.
