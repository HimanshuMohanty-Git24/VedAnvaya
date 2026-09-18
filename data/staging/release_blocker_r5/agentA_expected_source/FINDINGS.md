# GAP-ENTITY_COVERAGE-004 — Agent A, R5

Read-only investigation. No Neo4j writes, no git state changes, no file written outside
`data/staging/release_blocker_r5/agentA_expected_source/`.

## 1. What the entry measures, live

closure_measure: `MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n)`
Measured in this pass: **384 of 384**. The property key does not exist in the database.
`:DomainEntity` count is **384**, every key `VG:CONCEPT:*`, every node also `:Concept`.

## 2. Origin of all 384, traced to the declaring file

Reproduced independently from the files (not taken from any prior report): parse every
`- concept_id:` block in the five registry fragments, and every keyed record in the six ritual
staging artifacts. Result: **384 / 384 resolved, 0 unresolved.**

| origin | rows | file |
|---|---|---|
| **REGISTRY_YAML — hand-authored** | **229** | `data/registry/concepts.yaml` 91; `data/domain/vedagraph_domain_v2/domain_entities_material.yaml` 47; `domain_entities_concern_v3.yaml` 41; `domain_entities_concern.yaml` 29; `domain_entities_ritual_v3.yaml` 21 |
| **RITUAL_JSONL — corpus-measured** | **155** | `data/staging/ritual/rites.jsonl` 92; `implements.jsonl` 18; `materials.jsonl` 14; `actions.jsonl` 14; `roles.jsonl` 9; `offerings.jsonl` 8 |

**76 keys appear in BOTH** a registry fragment and a ritual artifact — those are the
`node_status: EXISTING` rows the ritual wave re-measured rather than created. First
declaration, and therefore origin, is the registry fragment.

The registry-fragment record schema is
`concept_id / preferred_label_sa / preferred_label_en / node_type / definition / aliases_sa /
aliases_en / broader / related_devatas`. **That schema has no bibliographic field at all** —
there is nowhere in it for an external source to be recorded, which is the mechanical reason
this gap exists.

The ritual-artifact record schema carries `existence_evidence_type`, `samhita_attested`,
`samhita_attestation_count`, `samhita_attestation_by_veda`, `samhita_attestation_examples`,
`supplementary_attestation_count`, `supplementary_attestation_by_work` and an `evidence[]`
array of `{supplementary_key, citation, evidence_source_type, quote, translation}`. Every
`citation` in it is a **text locus** ("SBM 3.1.3.1.5", "KausS 1.7.5") paired with an **in-repo**
passage key `VG:SUPP:<WORK>:<addr>`. That is in-corpus attestation, not an external published
expectation.

## 3. The prior pass's 229/155 claim — verified in part, falsified in part

The claim, verbatim from `data/staging/release_blocker_r4/agent_b_receipt.json:515`:

> "229 from concept registries with NO external source citation and 155 from ritual registries
> WITH existence_evidence_type"

| limb | measured | verdict |
|---|---|---|
| the **229 / 155 origin split** | 229 registry-origin, 155 ritual-origin, 0 unresolved | **CORRECT.** Independently reproduced. |
| "155 … **WITH existence_evidence_type**" | **228** nodes carry `existence_evidence_type`, not 155: 155 ritual-origin **plus 73 registry-origin** rows that the ritual wave re-measured. 156 carry none, and all 156 are registry-origin. | **WRONG, by 73.** The property is not coextensive with the origin split. |
| "229 … with **NO external source citation**" | Across all 384, **375** carry no `existence_evidence_citation`. Only **9** do. | **A SEVERE UNDERCOUNT, and attached to the wrong population.** |
| where the 9 external citations actually are | All 9 are **ritual-origin** — inside the "155", not the "229": `ACCHAVAKA-PRIEST, BRAHMANACCHAMSIN-PRIEST, GRAVASTUT-PRIEST, MAITRAVARUNA-PRIEST, PRASTOTR-PRIEST, PRATIHARTR-PRIEST, PRATIPRASTHATR-PRIEST, SUBRAHMANYA-PRIEST, UNNETR-PRIEST`, all carrying `existence_evidence_citation: "SankhSS 13.14.1"` and `existence_evidence_translation_citation: "W. Caland, Sankhayana-Srautasutra"`. | The claim implies the cited rows are the 155 and the uncited ones the 229. The reality is the opposite polarity: the only cited rows in the whole registry are nine ritual-origin priests. |

So the claim's split is right and its two predicates are both attached to the wrong side. The
real headline is much starker than 229: **375 of 384 entities have no external citation of any
kind, and the 9 that do cite a Srautasutra, not a Samhita.**

## 4. The five-class partition

`agentA_expected_source/expectation_origin_rows.jsonl` — **384 rows, all 384 present, 384
distinct keys, 0 skipped.** sha256 `1a2b2f006d08fdd13fdacefe3952810625c2b4222f773f7b9ef5e896c3ff6ae7`.

| class | rows | share |
|---|---|---|
| **A** EXPLICITLY_EXPECTED_BY_A_SOURCE | **161** | 41.9% |
| **B** DERIVED_FROM_AN_INTERNAL_CURATED_REGISTRY | **127** | 33.1% |
| **C** DERIVED_FROM_CORPUS_INVENTORY | **79** | 20.6% |
| **D** PRODUCT_EXPECTATION | **17** | 4.4% |
| **E** UNSUPPORTED_LEGACY_EXPECTATION | **0** | 0% |

Class x internal origin:

| class | REGISTRY_YAML | RITUAL_JSONL |
|---|---|---|
| A | 119 | 42 |
| B | 72 | 55 |
| C | 23 | 56 |
| D | 15 | 2 |

`expected_source` is non-null on **exactly the 161 class-A rows** and null everywhere else;
`externally_expected` is true on **exactly those 161**. Rows with a non-null `expected_source`
outside class A: **0**. No generic source was applied to any row.

Every row also carries its internal origin regardless of class — `internal_origin_kind`,
`internal_origin_file`, `declared_in_both_registry_and_ritual_artifact`,
`node_existence_evidence_type`, `node_existence_evidence_citation`, live-graph edge counts,
`named_in_gap_registry`, `named_in_benchmark_question_sets`, and the full VEI match state. A
class-B/C/D row cannot be mistaken for an externally expected one, and a class-A row still
shows which internal file first declared it.

### Class rules, in precedence order
1. **A** — a VEI headword folds unambiguously to the key's Sanskrit segment, there is exactly
   one such entry, and that entry's body names a Samhita. `expected_source` = the full
   bibliographic citation with entry number and page.
2. **D** — not A, and the key is named in `data/gap_registry.json` as a gap subject or in a
   benchmark question set. The surface is named per row.
3. **C** — not A/D, ritual-origin, `samhita_attested: true` with a non-zero attestation count.
   The measurement is named per row (count, by-veda breakdown, and the live-graph edge counts).
4. **B** — not A/D/C. A named curated record exists. The file, the record key and the record's
   own justification text are quoted.
5. **E** — none of the above: no justification text, no measurement, no supplementary
   attestation, no external citation.

## 5. Class E is 0, and here is the audit of that claim

E=0 is a measured result, not an omission. The criterion fired on no row because **every one of
the 384 has a non-empty justification quote in its origin record: 0 rows have an empty one.**

The stratum a reviewer should still scrutinise, named rather than hidden:

- **106 rows** have no VEI headword, no gap/benchmark reference and `samhita_attested` not true.
  All 106 are class B.
- **53 of those 106** additionally have **zero** live-graph edges — no `MENTIONS_ENTITY`, no
  `ABOUT_CONCEPT`, no `ATTESTED_IN`. Their entire warrant is one Brahmana/Sutra quote in the
  ritual artifact, e.g. `VG:CONCEPT:AGNISTUT` → `KatySS 12.1.3 :: agniṣṭutsu caike`, four words.
- **65 rows in total** have zero live-graph edges of any kind (55 class B, 8 class A, 2 class C).

These are weakly supported, not unsupported. Every one names a file and a quote. If the owner
wants a stricter E — say, "warranted only by a quote shorter than N tokens and with zero corpus
edges" — that set is the 53 above and it is derivable from the staged rows without re-running
anything.

**A provenance anomaly found on the way, worth the owner's attention and not mine to fix.**
`data/staging/integration/wave3_import_plan.json` records the `RITUAL_ROLE_NODES` group as
`candidates: 0, filtered_out_by_require: 27` — the role group was filtered out of the WAVE_3
import. Yet 9 priests first declared in `roles.jsonl` (`ACCHAVAKA-PRIEST,
BRAHMANACCHAMSIN-PRIEST, GRAVASTUT-PRIEST, MAITRAVARUNA-PRIEST, PRASTOTR-PRIEST,
PRATIHARTR-PRIEST, PRATIPRASTHATR-PRIEST, SUBRAHMANYA-PRIEST, UNNETR-PRIEST`) are live nodes,
and they carry **no** `wave3_group`, while the 9 nodes that DO carry
`wave3_group: RITUAL_ROLE_NODES` are all pre-existing registry entries. The group tag is
inverted relative to what the ritual wave actually created, and 9 nodes are in the graph from a
group the import plan says it did not import.

## 6. The class-A external source — documented search, 2026-09-18

The registry's `closure_basis` is explicit that the previous pass **did not search** and
refused to claim BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE on a search nobody ran. This is the search.

**Queries run (WebSearch / WebFetch / direct HTTP, all on 2026-09-18):**
1. `Macdonell Keith Vedic Index of Names and Subjects public domain full text machine readable`
2. `index of Vedic realia plants animals metals list digital dataset open license`
3. `Cologne Digital Sanskrit Dictionaries "Vedic Index" VEI Macdonell Keith sanskrit-lexicon`
4. `WebFetch https://archive.org/details/vedic-index-of-names-and-subjects-vol-1-macdonell-and-keith` — rights field
5. `WebFetch https://cceh.github.io/kosh/docs/implementations/c-salt_sanskrit.html` — API shape
6. `WebFetch https://www.sanskrit-lexicon.uni-koeln.de/` — terms of use
7. `GET https://api.github.com/repos/cceh/c-salt_sanskrit_data` and `/contents/sa_en` — licence + inventory
8. `POST https://api.c-salt.uni-koeln.de/dicts/vei/graphql` — GraphQL introspection, then a live
   headword query
9. `GET https://raw.githubusercontent.com/cceh/c-salt_sanskrit_data/master/sa_en/vei/vei.xml` — the
   full encoding, 4,008,305 bytes, downloaded to a session scratch directory

### FOUND, and usable: the Vedic Index of Names and Subjects

**Macdonell, A. A. and Keith, A. B., *Vedic Index of Names and Subjects*, London: John Murray,
1912. 3,834 entries; 3,704 distinct SLP1 headwords; 3,588 distinct after folding to our ASCII
convention; 2,532 of the folded headwords have an entry body that names a Samhita.**

- **Lawfully usable — the underlying work.** Published 1912, therefore public domain. The
  archive.org scan `vedic-index-of-names-and-subjects-vol-1-macdonell-and-keith` states
  **CC0 1.0 Universal** and offers a 1.2 MB full-text `.txt`.
- **Machine-readable — the Cologne encoding.** The Cologne Digital Sanskrit Dictionaries hold it
  as dictionary `vei`, TEI-P5, live at
  `https://api.c-salt.uni-koeln.de/dicts/vei/graphql` (verified working: field `headword_slp1`,
  queryType `term|prefix|match|regexp|...`) and as a downloadable file in
  `github.com/cceh/c-salt_sanskrit_data`.
- **Licence caveat, recorded rather than glossed over.** The Cologne repo declares **no
  licence** (`license: null` via the GitHub API), `sanskrit-lexicon.uni-koeln.de` states **no
  terms of use** — only a citation request — and `vei.xml` carries the header comment
  `<!-- Copyright Universitat Koln 2013 -->`. So the *1912 text* is unencumbered and the
  *Cologne encoding of it* is not licence-cleared. The lawful route for shipping is the CC0
  archive.org full text, or a licence enquiry to the C-SALT team; the Cologne TEI is fine for
  this investigation and should not be redistributed on the current evidence.
- **Machine-alignable to our keys: measured, not assumed.** Folding SLP1 to our ASCII key
  convention matches **200 of the 384** entity keys. 14 are excluded as fold collisions and 25
  as multi-entry/ambiguous-sense, leaving **161 class-A rows**.

**The trapu test, which is the closure test's own example.** VEI entry `lemma_trapu_1205`,
p. 1-326, verbatim:

> "**Trapu** denotes 'tin' in the Atharvaveda [xi. 3, 8] and later. [Kāṭhaka Saṃhitā, xviii. 10;
> Maitrāyaṇī Saṃhitā, ii. 11, 5; Vājasaneyi Saṃhitā, xviii. 13 (all in enumerations of metals);
> Taittirīya Brāhmaṇa, iii. 12, 6, 5; ... In Taittirīya Saṃhitā, iv. 7, 5, 1, the form is
> *trapus*.]"

The index names trapu, cites **AVS xi.3.8** — the exact verse a human had to read — and cites
VSM xviii.13, the metals enumeration. So the source that would have found trapu without a human
reading the text **exists, is public domain, and is machine-alignable.** All six metals of
VSM 18.13 are present in it (`trapu, hiraRya, ayas, SyAma, loha, sIsa` in SLP1).

### Scope limit of the source, measured by exact headword probe

The Vedic Index deliberately omits mythology and abstract nouns. `agni` **absent**, `anna`
**absent**, `amfta` **absent**, while `yava`, `vrIhi`, `aja`, `go`, `godAna`, `vAsas`, `rajju`,
`kumBa` are present. Coverage of our labels is therefore 100% on Animal/Place/River/Metal/
Weapon/Tribe/Crop, 95% Plant, 91% Substance, 81% Offering, 78% Object — and 18% Ritual, 15%
Action, 0% Quality. Full table and the consequences in `coverage_report_design.md` section 4.
**This is the single most important caveat: the source closes the realia half of the registry
and cannot touch the ritual/abstract half.**

### Two candidates checked and rejected
- A general search for an open "index of Vedic realia" dataset returned only Ayurvedic plant
  and Sanskrit-MT corpora (Bhāvaprakāśanighaṇṭu-derived plant lists, a 360-plant JSON dataset,
  Mitrasaṃgraha). None is an index of what the **Saṃhitās** name, so none can serve as the
  declared expectation.
- `data/registry/sources.yaml:192` "Digital Rig Vedic Index (Anukramani), WSC 2023", already in
  the repo, is an **anukramaṇī** — ṛṣi, devatā and metre per hymn. It is not a lexicon of
  realia and cannot serve class A.

## 7. The coverage report actually finds something, today

Run for real, not designed in the abstract. Details and the full table in
`coverage_report_design.md` section 6.

- The **in-corpus** declared list, VSM 18.13, is **6 of 6 present**. It closes. Used alone it
  would certify the registry as complete, which is the trap.
- The **external** list finds misses the in-corpus list cannot. Of the 22 VEI entries whose body
  mentions "metal", **8 are in the registry and 14 are not.** Two of the 14 are
  `MISSING_AND_ATTESTED` — the external index says the Samhitas name them **and our own stored
  Sanskrit contains them**:
  - **`lohita`** — VEI: "used as a neuter substantive in the Atharvaveda (xi. 3, 7) to denote a
    metal, presumably 'copper'." Measured in our graph: **15 distinct mantras** contain it,
    including `VG:AV:SAU:K11:S003:V007`, whose PRIMARY_TEXT reads
    `śyāmám áyo 'sya māṃsā́ni lóhitam asya lóhitam ||7||` — **lohita twice, in the verse
    immediately before the trapu verse.** The registry holds `SYAMA-DARK-METAL` and `AYAS-METAL`
    from that same verse and has no node for `lohita`.
  - **`karmāra`** ("the smith") — VEI cites Rv x.72,2; Av iii.5,6; VS xvi.27; VS xxx.7. All four
    resolve against our corpus: **RV 10.72.2, AVS 3.5.6, VSM 16.27, VSM 30.7 — 4 of 4.** No
    registry node.
  - `kārṣṇāyasa` and `kṛṣṇāyasa` are Upaniṣad-only in VEI and are **correctly excluded** by the
    Samhita filter, which is the check that the filter works.

**Lohita is trapu's twin, one verse earlier, and it is still missing.** It was surfaced here by
a headword fold and one containment query, with no human reading anything — which is exactly
what the closure test asks for.

## 8. What I could not establish

1. **Sense agreement on the 161 class-A alignments: 0 human-reviewed.** The alignment is a
   lexical headword match. Every class-A row carries
   `vei_alignment_basis: "HEADWORD_LEXICAL_MATCH_SENSE_NOT_HUMAN_REVIEWED"`. Spot-reading ten at
   random found the senses correct (Ayas, Śvan, Prśniparṇi, Nyagrodha, Āsrāva, Potṛ, Vivāha,
   Dhī) and two where the source's sense is adjacent rather than identical:
   `UPASTARANA-UNDERLAYING` against VEI's *Upa-staraṇa* = "coverlet" (an object, not the act),
   and `BRAHMAN-FORMULATION` against a VEI entry that opens on the priestly-class sense. Those
   two should be reviewed before the field is treated as authoritative.
2. **The licence position on the Cologne TEI encoding.** No licence is declared anywhere; the
   file asserts Cologne copyright 2013. I did not resolve it, and it needs either a licence
   enquiry or a re-derivation from the CC0 archive.org text before anything ships.
3. **A Samhita-scoped subset of the VEI's own citations is not fully parsed.** I detected
   "this entry names a Samhita" by regex over the entry body (2,532 of 3,588 folded headwords).
   Turning each into structured loci — the `samhita_loci` field of the design's MISSING row — is
   a further parse I did not write. It is bounded and mechanical; the `karmāra` round-trip
   (4/4) shows it works, on one entry.
4. **The full `MISSING_AND_ATTESTED` list over all 2,532 headwords was not computed.** I ran it
   on the metals slice only (22 entries). The design specifies the query; running it over the
   whole index is the next step, and on the metals evidence it will not come back empty.
5. **Two VEI headwords are cited to works we do not hold** (Maitrāyaṇī and Kāṭhaka Saṃhitās).
   Those are `MISSING, OUT OF OUR CORPUS SCOPE` and must not be counted as registry defects.

## 9. Recommended registry disposition (stated, not applied)

**GAP-ENTITY_COVERAGE-004 — keep `STILL_IMPLEMENTATION_FIXABLE`, and update the fields.** The
closure_measure still reads 384 because nothing was written, but the entry's own reasoning has
moved on two of its three legs.

Recommended edits, for the lead:

- **`source_dependency`: change from a dependency to a satisfied one.** It reads "A published
  lexicon or index of Vedic realia to serve as the declared expectation." One exists, is public
  domain, is machine-readable and is machine-alignable: Macdonell and Keith, *Vedic Index of
  Names and Subjects*, London: John Murray, 1912; 3,834 entries; Cologne dictionary id `vei`.
  Record the licence caveat on the Cologne encoding, and record the scope limit (realia and
  names only; `agni`, `anna` and `amṛta` are absent by editorial scope).
- **Do NOT record `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`.** The search was run, dated and logged
  in section 6, and it found a usable source.
- **Correct the `closure_basis` figure.** Its stand-in for the internal half should be 375 of
  384 with no external citation, not 229; and 228 rows carry `existence_evidence_type`, not 155.
  Both corrections are in section 3.
- **Split the closure test**, because it is two tests with different difficulty:
  - **-004a** — the field exists and is honestly populated. Staged here: 384 rows,
    A 161 / B 127 / C 79 / D 17 / E 0, `expected_source` non-null on exactly the 161 class-A
    rows. Additive, unblocked, ready.
  - **-004b** — the coverage report names entities the expectation lists and the registry lacks.
    Designed in `coverage_report_design.md`, and already proven on the metals slice, where it
    returns `lohita` and `karmāra`. Still needs the full-index run.
- **Open a new gap, or extend -005, for what the report already found:** `lohita` (15 mantras,
  incl. AVS 11.3.7) and `karmāra` (4 mantras, 4/4 against VEI's own loci) are Samhita-attested
  in our own stored text and absent from the registry. GAP-ENTITY_COVERAGE-005's
  `implementation_dependency` says to keep trapu as the illustrative case rather than an open
  registry gap; `lohita` is the same case, unclosed, and it should not be kept illustrative.
- **Record `diagnostics_run` honestly:** `M_scope` RUN — the external index's scope is realia
  and names, not deities or abstract nouns, so the denominator is valid for 11 of our 22 labels
  and undefined for the rest. `E_transliteration_script` RUN — the SLP1-to-ASCII fold is lossy
  and collides on 14 of 200 matches; those are excluded by name, not guessed.

**Do not let the field be "completed".** The temptation this gap creates is to write one
citation onto 384 rows and watch the measure go to 0. The staged rows deliberately leave
`expected_source` null on 223 of 384 and `externally_expected` false on those same 223. A
closure that fills all 384 should be rejected on sight: the field's purpose is provenance, and
223 of these entities genuinely have no external expectation behind them.
