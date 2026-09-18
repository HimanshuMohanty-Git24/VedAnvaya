# GAP-SAMAVEDA_MUSIC-003 — Agent A, R5

Read-only investigation. No Neo4j writes, no git state changes, no file written outside
`data/staging/release_blocker_r5/agentA_samaveda_music/`.

## 1. What the entry actually measures

closure_measure: `MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)`
Measured live in this pass: **1844 of 1844**. `CALL db.propertyKeys()` filtered for
running / samhita_num returns **[]** — the property key does not exist in the database.

The closure_test has TWO clauses:

1. "Every Samavedic mantra exposes its running Samhita number" — measured by the
   closure_measure above. Additive, source-complete, no owner decision involved.
2. "re-deriving the MUSICALIZED_AS edges from the graph alone reproduces all 495" —
   measured by GAP-SAMAVEDA_MUSIC-002's measure, `MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)`
   = **0**; `CALL db.relationshipTypes()` filtered for MUSIC returns **[]**.

Clause 2 cannot be satisfied by anything in this slice, and not only because of the owner
gate. Measured: `MATCH (n) WHERE n.work_id STARTS WITH 'VG:WORK:SV:KAU:GANA' RETURN count(n)`
= **0**; `MATCH (n) WHERE n.canonical_key STARTS WITH 'VG:SV:KAU:GANA' RETURN count(n)` = **0**;
`MATCH (w:Work) WHERE w.veda='SV'` returns exactly one work, VG:WORK:SV:KAU. The *object end*
of all 495 proposed edges does not exist in the graph. Clause 2 therefore needs (a) four gana
Work nodes whose identity_status is still PROPOSED_FOR_LEAD_ADJUDICATION, (b) 657 gana unit
nodes, (c) the MUSICALIZED_AS type, and (d) the running number. Only (d) is in scope here.

## 2. Five separate things, kept separate

| bucket | what exists | where | status |
|---|---|---|---|
| **1. Running Samhita number** | 1,844 source-published numbers, range 1..1875, 31 documented gaps | `data/canonical/samaveda_arcika_v1/citations.jsonl` (system WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER) and `text_versions.jsonl` source_locator | **CANONICAL, unimported.** Staged here. |
| **2. Musical notation** | 1,136 arcika verses with source-explicit Kauthuma numeric svara; 657 gana units of which 86 carry inline Unicode marks, 421 carry none, 555 carry only a page-scan image | `data/staging/samaveda_music/rows.jsonl` (layer ARCIKA_NOTATION), `gana_units.jsonl` | **STAGED, unimported.** Belongs to -002. |
| **3. Audio** | 475 Commons Ogg gana performances, byte-hashed, licensed; **0** verse-scoped arcika recordings over an assessed population of 1,844 | `performances.jsonl`, `proofs/arcika-verse-audio-absence.json` | **VERIFIED ZERO** for arcika verses; 0 minutes heard. Behind OWNER_DECISION_E_AUDIO_GATE. |
| **4. Translation** | none for SV in this domain | `data/canonical/samaveda_arcika_v1/translations.jsonl` is 0 bytes | absent, out of scope |
| **5. Arcika vs Gana structure** | Arcika = VG:WORK:SV:KAU, 1,844 mantras, in the graph. Gana = four **separate** works, 657 units, **not** in the graph | `gana_works.jsonl`, `gana_units.jsonl` | Gana is a different work; the artifact says so: "It shares no key with VG:WORK:SV:KAU and no arcika count denominates over it." |

Only bucket 1 is what -003's closure_measure measures. Buckets 2, 3 and 5 are -002's substance
and are owner-gated.

## 3. Inventory

### 3.1 data/canonical/samaveda_arcika_v1/ — the canonical arcika release

| file | rows | content |
|---|---|---|
| `passages.jsonl` | 1,844 MANTRA plus containers | Kauthuma arcika structure. Coordinate grain: collection + prapathaka/ardha + dasati + verse, e.g. VG:SV:KAU:UTTARA:P04:R02:D01:V01. |
| `citations.jsonl` | 3,688 = 1,844 x 2 | 1,844 VG_SV_KAUTHUMA_COLLECTION_COORDINATE (is_canonical true) plus **1,844 WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER, label "SV <n>", is_canonical false, source_id WIKISOURCE_SA**. |
| `text_versions.jsonl` | 1,844 | source_locator is per-verse and verbatim: "WS CHANDA.P1.D3 RN33". The RN suffix is the running number. |
| `qa_issues.jsonl` | 39 | REFERENT_UNRESOLVED, each carrying details.source_running_number. **31 distinct values.** |
| `source_assertions.jsonl` | 69 | source_declared_local_verse_index, locators of the form "WS CHANDA.P1.D4 RN35". |
| `audio_recordings.jsonl`, `audio_segments.jsonl`, `translations.jsonl`, `traditional_metadata.jsonl` | 0 | empty files. |

Source: Sanskrit Wikisource, Kauthuma Samhita (WIKISOURCE_SA). Recension: **Kauthuma**,
evidenced by the page-title path. Notation: **not present** in this artifact — it is the
unaccented mula.

### 3.2 data/staging/samaveda_music/ — Wave 3 agent 5, algorithm_version samaveda-music-1.0.0

| file / row_kind | rows | coordinate grain | maps to canonical Kauthuma arcika? by what join? | notation source-explicit? | deterministic? | ARCIKA or GANA |
|---|---|---|---|---|---|---|
| `rows.jsonl` ARCIKA_NOTATION | 1,136 | arcika canonical_key | YES — normalised text equality plus LCS order-consistency against the 1..1875 sequence; mapping_confidence EXACT on all. The page's printed numerals were explicitly NOT used to join. | **YES.** 1,136/1,136 have tone_mark_count > 0, notation_system KAUTHUMA_NUMERIC_SVARA, 0 private-use codepoints, 0 U+0301. | yes | **ARCIKA** |
| `rows.jsonl` GANA_RENDERING | 332 rows carrying **495** renderings (sum of rendering_count = 495, verified) | arcika canonical_key -> gana unit key | YES — the gana page prints the **arcika running number** AND the arcika text we hold appears verbatim on that page; two independent signals had to agree. | object notation is per gana unit, see below | yes | **GANA** at the object end |
| `rows.jsonl` GANA_PERFORMANCE_AT_ARCIKA_CONTAINER_SCOPE | 3 | arcika **container** (ardha/dasati), never a verse | container only | n/a | yes | GANA audio pinned at ARCIKA container scope |
| `gana_units.jsonl` | 657 (UHAGANA 356, GRAMAGEYA 175, UHYAGANA 65, ARANYAKAGEYA 61) | VG:SV:KAU:GANA:{BOOK}:{path-slug} — gana / saman unit, **not** an arcika coordinate | only the 332 reached by the running-number join | 86 carry inline Unicode svara; 421 carry none; 555 carry only a page-scan image | yes | **GANA** |
| `gana_works.jsonl` | 4 | work | no | n/a | n/a | **GANA**; all four identity_status PROPOSED_FOR_LEAD_ADJUDICATION |
| `performances.jsonl` | 475 | one Ogg file to one gana page (alignment_granularity WHOLE_FILE_SHARED_ACROSS_PAGES) | no | n/a | yes — sha256 over fetched bytes, sha1 re-derived and matched to MediaWiki 475/475, duration re-measured from the Ogg granulepos 474/474 | **GANA** |
| `rejected.jsonl` | 724 | mixed | n/a | n/a | n/a | 16 REJECTED (e.g. "book index page, not a gana unit") plus 708 UNRESOLVED arcika verses where the accented witness text differs from ours |
| `sources.jsonl` | 4 | — | — | — | — | see below |

Source records, verbatim identities from sources.jsonl:

- WIKISOURCE_SA.SV.KAU.SASVARA_PURNA — Sanskrit Wikisource "sasvara purna" (fully accented
  arcika), page_id 93360, revid 231091 pinned, revision timestamp 2020-04-21T01:24:02Z,
  CC BY-SA 4.0, authority_tier COMMUNITY_TRANSCRIPTION. Recension Kauthuma, evidenced by the
  title path kauthumiya and by the body's own purvarcikah ... navamaprapathakah headers.
- WIKISOURCE_SA.SV.KAU.GANA — the four Kauthuma gana books, per-page revids on every row,
  CC BY-SA 4.0, COMMUNITY_TRANSCRIPTION.
- COMMONS.SV.KAU.SAMAN.AUDIO — 475 Ogg files, licence verified per file via imageinfo:
  459 CC BY-SA 4.0, 16 CC0, 0 unstated.
- IISH.SV.GANA.RECORDING — archive.org IISHSamaVeda. authority_tier UNSTATED_RIGHTS, licence
  "NONE STATED", recension "NOT ESTABLISHED", **zero bytes fetched**, no row points into it.
  Referenced for the record only.

Notation census (proofs/notation-codepoint-census.json): 108,160 tone marks over 667 pages and
1,750,419 characters examined. **98.09%** sit in Devanagari Extended U+A8E0-U+A8F1 (106,094)
and only **1.91%** in Vedic Extensions U+1CD0/U+1CD2 (2,066), so an extractor scoped to the
Vedic Extensions block would find 2,066 marks and miss 106,094. A further **17,928**
avagraha-digit runs carry notation as ordinary Devanagari digits and are invisible to any
combining-mark census. 14 private-use codepoints total, 3 of them on gana pages.

### 3.3 Other Samaveda / notation material checked

- `data/staging/loar_samaveda/inventory.jsonl` — **22 rows**, Royal Danish Library LOAR
  cassette items. Grain: LOAR item handle / cassette identifier. Contains **no** running
  number, **no** notation, **no** arcika coordinate. Every row is NEEDS_AUDIBLE_REVIEW with
  coverage_claimed false; the first row is classified NOT_SAMAVEDIC. Irrelevant to -003.
- `data/canonical/samaveda_pilot_v1/` — the superseded pilot.
- `src/vedagraph/ingest/adapters/samaveda_gretil.py` — GRETIL; the module header records it as
  rights-encumbered and used only for structural comparison, never as a text source.
- `docs/reports/data-completeness/SCHEMA_MIGRATION_CARDS.md:90` already specifies the fix:
  "An additive property running_samhita_number on Samavedic :Mantra nodes, 1,844 values,
  already captured in the agent's citations.jsonl."
- `docs/reports/VEDAGRAPH_ONTOLOGY_REFERENCE_V3.md:611` — MUSICALIZED_AS, endpoints
  Passage -> Passage, edges 0, **"asserts: This Rigvedic verse is sung as this Samavedic
  melody."** That gloss is RV->SV and must be widened before it can honestly carry an
  SV-arcika -> gana edge. Confirmed; not mine to change.
- `grep -ril "running_samhita|running samhita|samhita_number|running_number"` over
  data src docs scripts returns 40 files. Every one is either the canonical arcika artifact,
  the samaveda_music staging artifact, the gap registry, a prior blocker-pass receipt, or the
  agent-7 derivation scripts named in section 5. No other body of Samavedic numbering material
  exists in the repo.

## 4. Why running_samhita_number is 0 of 1844

Not a source absence and not a derivation failure. **The importer dropped the field.**

- The canonical artifact carries the number twice per verse: as a non-canonical Citation row
  and as the RN suffix of the text_versions.jsonl source_locator.
- The graph has **no :Citation label at all** (`CALL db.labels()` filtered for citat returns an
  empty list), so the 1,844 citation rows had nowhere to land.
- The graph has **3,688** SV TextVersions, two per mantra, via HAS_TEXT_VERSION. The 1,844
  SEARCH_DERIVATIVE rows (VEDAGRAPH.SV.SEARCH_NORMALIZED) carry source_locator =
  "derived:normalize_nfc+fold_devanagari_source_conventions+to_iast+comparison_form:SEARCH_NORMALIZED",
  a derivation recipe. The **1,844 PRIMARY_TEXT rows (WIKISOURCE_SA.SV.KAU.ARCIKA_MULA) — the
  ones that hold the real locator in the canonical file — carry source_locator null**, and
  provenance and provenance_note are null on them too. Measured: PRIMARY_TEXT SV TextVersions
  with a non-null source_locator = **0**.

### Correction to a prior claim

The R1 closure_basis states: "the source_locator that does exist on 1,844 SV TextVersion rows
holds ONE distinct value across all 1,844 ... which is not a locator." The conclusion is right
but the population is wrong. There are **3,688** SV TextVersion rows, not 1,844. The recipe is
on the 1,844 derivative rows; the 1,844 primary rows are **null**. The defect is sharper than
"the graph has a useless locator": the graph has the locator field populated on exactly the
rows where it is meaningless, and null on exactly the rows where the source filled it in.

### The registry's own source_dependency claim, verified

source_dependency reads "NONE. The number is already captured in the staging artifact" —
**verified in substance, wrong in location.** The number is in a **canonical** artifact
(data/canonical/samaveda_arcika_v1/, files dated 2026-09-07), not a staging one. The staging
artifact data/staging/samaveda_music/ holds a running number for only **332** verses, and holds
it as the gana source's printed number (arcika_running_number_printed_by_source), not as a
property of the arcika verse. Anyone acting on the registry text alone and looking only under
data/staging/ would find 332 of 1,844 and conclude the claim was false.

## 5. The decisive judgement: is the number independently alignable?

### Falsifier, stated before testing

> If the running number is produced by enumerate() over our own corpus ordering, then
> (a) its value set will be exactly 1..1844, contiguous, no gaps, no collisions, and
> (b) it will agree on **100%** of the 332 verses where a second, different source (the
> sa.wikisource gana page subtree) independently prints an arcika running number.
> If instead it is source-published, it will show gaps wherever our corpus falls short of the
> edition's spine, and an enumerate() reconstruction will DISAGREE with the second source.

### Test and result

| test | result |
|---|---|
| value set of the 1,844 numbers | min **1**, max **1875**, **1,844 distinct**, **0 collisions**, **31 gaps** |
| the 31 gaps | 1107-1115, 1172-1174, 1178-1186, 1241-1243, 1280-1285, 1315 |
| is each gap explained by a recorded source defect? | **YES, 31 of 31.** qa_issues.jsonl holds 39 REFERENT_UNRESOLVED rows over exactly **31 distinct** source_running_number values, and that set is **identical** to the gap set. 0 gaps unexplained; 0 withheld numbers that are not gaps. |
| 1875 minus 1844 | **31** — equal to the gap count, and to edition_spine_declared 1875 minus graph_holds 1844 |
| citations.jsonl "SV n" vs text_versions.jsonl "RNn", same passage_id | **1844 of 1844 agree** (two independent files inside the canonical artifact) |
| canonical keys in citations.jsonl vs the live graph's 1,844 SV Mantra keys | **identical sets**; 0 in one and not the other |
| number strictly increasing along the graph's own structural walk (depth-first over parent_key, sequence_in_parent) | **TRUE**, 1,844 of 1,844, zero inversions |
| **CONTROL: agreement with the gana pages' independently printed number, 332 verses** | **source-published number: 332 of 332.** enumerate() over our own structural walk: **256 of 332** |

### Verdict: NOT a fake running number. It is source-published and independently alignable.

The falsifier fired against the fake-number hypothesis on both limbs.

1. An enumerate() would be gapless 1..1844. This is 1..1875 with 31 gaps, and every gap is a
   verse the source printed and the adapter deliberately **withheld** because the dasati's
   printed run was non-contiguous or a number was printed twice. The gaps are the source's
   recorded defects, not our arithmetic.
2. enumerate() is **wrong on 76 of 332** verses against a second publisher's printed number.
   Its offset climbs 0, 9, 12, 21, 24, 30, 31 across seven localised steps and ends at exactly
   the 31-verse deficit. The source-published number is wrong on **none**.

Direct source statement, src/vedagraph/ingest/adapters/samaveda_wikisource.py docstring:

> "**The verse number printed in the body is the RUNNING number of the whole samhita
> (1..1875), not a dasati-local index.** Page 1.1.1.5 prints 45..54, not 1..10."

Prior-work note, and it is good work:
data/staging/final_closure_sprint/agent7/sv_running_number_derivation.py already ran the
structural-walk derivation and recorded agree 256, disagree 76,
reproduces_the_source_numbering false. I reproduced those figures exactly. Its result should be
read as "the derivation is not a substitute for the published number", which is the same
conclusion reached here from the opposite direction.

## 6. What is staged

`agentA_samaveda_music/running_samhita_number.jsonl` — **1,844 rows**, one per SV mantra, in
structural-walk order. sha256 of the file:
d7c42150008e549b5284270047b2e1cdbee542c43ba2067cb71cba5dd9a9e214

Per-row fields:

- canonical_key, running_samhita_number
- source_artifact — data/canonical/samaveda_arcika_v1/citations.jsonl (system
  WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER), corroborated by text_versions.jsonl source_locator
- source_locator_verbatim — the real per-verse locator, e.g. "WS CHANDA.P1.D3 RN33"
- join_method — the full deterministic recipe (passage_id to entity_id to canonical_key)
- join_is_deterministic — **true on 1844 of 1844**
- evidence_quote — the citation label, the locator string, the adapter's own statement, and for
  332 rows the second source's printed number and its page locator
- roundtrip_number_to_key_is_1to1 — **true on 1844 of 1844**
- structural_order_rank — 1..1844 along the graph's own walk
- order_consistent_with_structural_order — **true**
- corroborated_by_second_source_gana_page — **true on 332, false on 0, null on 1,512**. null
  means no gana page prints this verse's number; it is not a disagreement.

Collisions: **0**. Gaps in the number sequence: **31**, enumerated in section 5, all explained.

`notation_rows.jsonl` is **deliberately NOT staged.** Instruction 7 is conditional on no
alignable number existing, and one does exist. Restaging the notation would duplicate
data/staging/samaveda_music/rows.jsonl in substance and would be staging work for
GAP-SAMAVEDA_MUSIC-002, which is behind OWNER_DECISION_E_AUDIO_GATE and is not mine to move.
For the record, the notation evidence **is** validated and source-explicit: 1,136 of 1,136
arcika rows with evidence_layer SOURCE_EXPLICIT, recension_verified true, belongs_to ARCIKA,
recension Kauthuma, 0 defects over 12 exhaustive checks covering 11,193 records. It is already
staged, correctly, under -002.

## 7. What cannot be established, and exactly why

1. **Clause 2 cannot be satisfied from this slice.** 0 of the 495 edges' object nodes exist in
   the graph. The four gana Works are PROPOSED_FOR_LEAD_ADJUDICATION, minting them is an owner
   decision, and MUSICALIZED_AS would additionally need its RV-to-SV gloss widened. Importing
   the running number is necessary for clause 2 and nowhere near sufficient.
2. **I did not re-fetch the live Wikisource page.** The 1,844 numbers are verified against two
   files inside the canonical artifact (1844 of 1844 agreement) and against a second,
   independent Wikisource subtree (332 of 332 agreement). The 1,512 verses with no gana-page
   corroboration rest on one publisher's transcription, pinned at page_id 93360 / revid 231091.
   That is the strongest evidence available without a network re-fetch, which I did not perform.
3. **The number is a locator, not a text claim.** Nothing here verifies accent or text; the 708
   UNRESOLVED accented-witness disagreements in rejected.jsonl are untouched by this slice.

## 8. Recommended registry disposition (stated, not applied)

**GAP-SAMAVEDA_MUSIC-003 — keep STILL_IMPLEMENTATION_FIXABLE. Do not close it, and do not mark
it blocked.** Clause 1 is now source-complete and evidence-complete: 1,844 staged rows with a
verbatim per-verse locator, 0 collisions, 31 explained gaps, 332 of 332 second-source
corroboration, 256 of 332 for the fake alternative. But the closure_measure still reads 1844
because nothing has been imported and this agent does not write. When the staged rows land, the
measure goes to 0 and clause 1 closes on its own terms.

Recommended edits, for the lead to apply:

- Correct source_dependency to name the real location:
  data/canonical/samaveda_arcika_v1/citations.jsonl and text_versions.jsonl, **not** "the
  staging artifact". Set source_availability to source-available-in-repo.
- Split the entry, so clause 2 cannot terminate clause 1:
  - **-003a**, running number: closure_measure unchanged, STILL_IMPLEMENTATION_FIXABLE,
    unblocked, staged and ready.
  - **-003b**, re-derive the 495 edges from the graph alone: BLOCKED_OWNER_DECISION_REQUIRED
    behind OWNER_DECISION_E_AUDIO_GATE **and** the gana Work adjudication, cross-referenced
    to -002.
- Record diagnostics_run B_source_coordinate_system and I_sort_order as RUN, with the result
  above: the source coordinate system is the printed 1..1875 running series, and our own sort
  order is **not** a valid substitute for it (256 of 332).

**Separate finding, not a -003 edit: an import-fidelity defect.** The SV PRIMARY_TEXT
TextVersions carry source_locator null while the canonical file has a real locator on all
1,844. That is a general rows-sent-versus-rows-landed bug, not a Samaveda-specific one, and it
is worth probing on RV, YV and AV before it is patched only here.

**GAP-SAMAVEDA_MUSIC-002 — leave exactly as it is.** Not mine. Its measure is genuinely 0, the
melodic layer is wholly unbuilt, and its BLOCKED_OWNER_DECISION_REQUIRED behind
OWNER_DECISION_E_AUDIO_GATE is correct on the evidence I saw.
