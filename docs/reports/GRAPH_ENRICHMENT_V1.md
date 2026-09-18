# Graph Enrichment V1

Starting commit: **`fc6076a`** (`feat: add the Neo4j graph projection layer for all four Vedas`)
Branch: `semantic-pilot-v1`
Pipeline version: `vedagraph-graph-enrichment-v1`

This release turns a corpus graph into a discovery graph. The structural layer already held
22,537 passages across four Vedas and could answer "what is RV 1.1.1"; it could not answer
"where else does this verse appear", "what else is about fire", or "why are these two
connected". It can now, and every answer carries its own evidence.

---

## 1. What the layer had to work around

Three properties of the corpus determined the whole design, and none of them is optional
to handle.

**The four Vedas are not in the same script.** RV and AV are Latin (GRETIL); SV and YV are
Devanagari. `agním` and `अग्निम्` are the same word and share no code point, so a
cross-script pair *cannot* match at any byte-level surface. Every match therefore records
which surface it was reached on, and `reachable_levels()` states up front which levels a
given pair could possibly reach — so a level absent because it is impossible is
distinguishable from a level absent because the texts differ.

**The Samaveda is written in continuous sandhi.** It prints `देवीरभिष्टये` where the
Rigveda prints `devīr abhiṣṭaye`. Same two words. A token-based comparison sees zero
overlap; a character-based one sees an exact match. Without a word-boundary-free surface,
RV/SV discovery — the largest body of genuine cross-Veda reuse in the corpus — mostly does
not work. This is also why token Jaccard is *stored* on every parallel row but excluded
from the similarity blend.

**The Samaveda has no English translation at all.** Zero, in any source. Concept coverage
for SV therefore rests entirely on the Sanskrit path, and any per-Veda number that looks
low for SV needs that context rather than a fix.

---

## 2. Graph backlog, closed first

### 2a. The two colliding translation IDs

Root cause, traced to the pinned raw snapshots: **the Wikisource Griffith pages print one
verse number twice.** RV 1.91 numbers its verses `... 15. 16. 17. 16. 19. ...` with 18
absent; RV 5.44 numbers `... 12. 13. 11. 15.` with 14 absent. Two different verses were
therefore filed under one mantra, and since `translation_id` derives from
`(passage, artifact, revision)`, both derived the same id and the loader's `MERGE`
silently discarded one of each pair.

Not an ingestion bug — an upstream typographical error, faithfully reproduced.

**Fixed without touching the corpus.** `data/canonical/rigveda_full_v1/translations.jsonl`
is a hashed input of the sealed semantic V3.2 freeze. That was verified empirically, not
assumed: adding a `graph` extra to `pyproject.toml` was tried, made
`test_the_preserved_v3_1_draft_freeze_detects_the_v3_2_contract_change` fail, and was
reverted. So the correction lives in `data/registry/upstream_corrections.yaml` and is
applied at projection time by `vedagraph.graph.corrections`.

Three properties make that safe:

- a correction is matched on **text content**, never on the colliding id — that the id
  cannot distinguish the two rows *is* the defect;
- the re-derived id uses the standard derivation with the corrected passage, so it is the
  id the row would have had if the page had printed the right number, not a de-collision
  suffix;
- a declared correction that matches **no** row raises. A registry documenting fixes the
  data does not contain is worse than no registry.

| | before | after |
|---|---:|---:|
| Translation nodes in the live graph | 17,281 | **17,283** |
| RV 1.91.18 translations | 0 | **1** |
| RV 5.44.14 translations | 0 | **1** |

Two mantras that had no English at all now have Griffith's.

### 2b. neo4j dependency handling

**Preserved in `infra/requirements-graph.txt`**, as instructed, and the reason was
re-verified this session rather than inherited: `pyproject.toml` is inside the freeze and
adding to it fails a sealed test. No clean non-freeze-breaking alternative exists while the
full-corpus semantic run is blocked.

### 2c. AV QA items

**Projected — and for all four Vedas, not just the Atharvaveda.** 915 `QAIssue` nodes
(RV 842, SV 39, YV 25, **AV 9**) attached to their `Work` by `HAS_QA_ISSUE`. A Veda-specific
branch would have been *more* code than the uniform pass and would have left the Rigveda's
842 findings invisible for no reason. Issue ids are content-derived, so they are stable
across rebuilds.

### 2d. A defect found while verifying the above

The loader logged 10,527 `HAS_CHANDAS` rows against 10,523 edges in the database. The gap
is benign — the anukramaṇī asserts Pragātha for RV 8.46.25–28 through two overlapping range
scopes and `MERGE` correctly collapses them — but the loader was reporting *rows sent* as
though they were edges. It now reports distinct edges and names the collapse. A count that
does not mean what it says costs an hour of forensics the next time someone reads it.

---

## 3. Agents

| Agent | Scope | Outcome |
|---|---|---|
| A (this session) | Coordination, shared contracts, backlog, analytics, validation, queries, semantic packets | contracts + 4 backlog items + 25 queries |
| B | Cross-Veda exact and near matching | 6,271 rows; found a defect in A's `surfaces.py` |
| C | Formula discovery | 4,825 nodes, 22,686 occurrences |
| D | Concept ontology and assignment | 89 concepts, 47,542 assertions |
| E | Bounded semantic extraction | see §8 |
| F | Neo4j projection, schema, loader | 38 schema statements, injection-proof loader |
| G | Adversarial QA | see §11 |

### The defect Agent B found in a shared contract

`surfaces.build_surfaces` transliterated the **raw** source. The accented Vajasaneyi layer
types visarga as an ASCII colon in 893 of its 1,975 mantras; `fold_devanagari_source_conventions`
rewrites that to U+0903 but is gated on the text containing Devanagari — correctly, since a
colon in Latin text is punctuation. Transliterating first defeated the gate: the colon
survived, and `strip_editorial_marks` then deleted it as a separator. A colon-visarga mantra
and a real-visarga mantra compared **equal** on the Devanagari surface and **unequal** once
folded — on the only surfaces a cross-script pair can be compared on at all.

Fixed in `surfaces.py`, where it benefits every stage:

| | before fix | after fix |
|---|---:|---:|
| RV↔YV identities | 90 | **189** |
| AV↔YV identities | 21 | **48** |
| SV↔YV identities | 75 | **83** |
| **total identical cross-Veda pairs** | 1,404 | **1,538** |

Agent B also disproved an assumption stated in that module: **the surfaces are not strictly
nested.** A pair can match at `ACCENT_INSENSITIVE` and fail at `SCRIPT_FOLDED`, because the
fold is lossy in ways the Devanagari surface is not. Bucketing per level rather than on the
weakest level is what keeps those pairs. The false claim has been removed from the docstring.

---

## 4. Graph size

| | nodes | relationships |
|---|---:|---:|
| Session start (`fc6076a`) | 94,753 | 134,065 |
| After backlog fixes | 95,670 | 134,982 |
| **After enrichment** | **100,584** | **212,336** |

New node labels: `Concept` (89), `Formula` (4,825), `QAIssue` (915).

New relationship types: `NEAR_PARALLEL_OF`, `VARIANT_OF`, `REUSES_TEXT_FROM`,
`USES_FORMULA`, `ABOUT_CONCEPT`, `BROADER_THAN`, `DEVATA_ASSOCIATED_WITH`, `HAS_QA_ISSUE`.

The arithmetic closes exactly, which is the cheapest available proof that nothing was lost
in the load and nothing was invented by it:

```
nodes         95,670 + 89 Concept + 4,825 Formula                    = 100,584  ✓
relationships 134,982 + 47,542 ABOUT_CONCEPT + 22,686 USES_FORMULA
                      + 3,049 NEAR + 1,684 REUSES + 788 VARIANT
                      + 750 EXACT + 101 DEVATA_ASSOC + 18 BROADER
                      + 736 semantic candidates                       = 212,336  ✓
```

`EXACT_PARALLEL_OF` is shared with the existing within-Rigveda lexical layer; the two are
separable because every enrichment edge carries `pipeline_version` and the lexical edges do
not, and `pipeline_version` is inside the `MERGE` pattern so the layers cannot overwrite
each other.

---

## 5. The relationship matrix

Cross-Veda edges by pair and predicate, read from the live database.

| pair | EXACT | VARIANT | NEAR | REUSES | relationships | **distinct pairs** |
|---|---:|---:|---:|---:|---:|---:|
| RV↔SV | 89 | 415 | 1,180 | 1,684 | 3,368 | **1,684** |
| RV↔AV | 551 | 22 | 752 | 0 | 1,325 | **1,325** |
| RV↔YV | 24 | 165 | 473 | 0 | 662 | **662** |
| SV↔AV | 9 | 132 | 326 | 0 | 467 | **467** |
| SV↔YV | 70 | 13 | 156 | 0 | 239 | **239** |
| YV↔AV | 7 | 41 | 162 | 0 | 210 | **210** |
| **total** | **750** | **788** | **3,049** | **1,684** | **6,271** | **4,587** |

**The predicate columns must not be summed on their own.** ``REUSES_TEXT_FROM`` restates a
symmetric row as a directed borrowing rather than adding a finding, so RV↔SV's 3,368
relationships stand over 1,684 distinct passage pairs. Adversarial QA caught this report
double-counting them; ``distinct_pairs`` is now carried in every cell of
``analytics.json`` so the table is safe to add up.

The shape of this table is itself a result. RV↔AV is dominated by `EXACT_PARALLEL_OF`
because both are Latin GRETIL editions with the same word division. RV↔SV is dominated by
`VARIANT_OF` and `NEAR_PARALLEL_OF` because the Samaveda writes continuous sandhi — the
verses are the same, the spelling of word boundaries is not. SV↔YV is mostly exact because
both are Devanagari. Collapsing these into one `PARALLEL_TO` would have destroyed the
distinction that makes the table readable.

`REUSES_TEXT_FROM` is directed and is asserted for **RV↔SV only**, subject = SV. That is
not a similarity finding: the Sāmaveda Ārcika *is* a collection of Rigvedic verses arranged
for chanting, and its own tradition identifies the Rigveda as its source. Every other pair
is left undirected, because asserting a direction there would be a chronology claim the
corpus does not support.

### Formula sharing (formulas attested in both Vedas)

| pair | shared formulas |
|---|---:|
| RV↔AV | 2,086 |
| RV↔SV | 1,862 |
| RV↔YV | 1,278 |
| YV↔AV | 907 |
| SV↔AV | 843 |
| SV↔YV | 560 |

### Concept connections (concepts attested in both Vedas)

| pair | shared concepts |
|---|---:|
| RV↔AV | 89 / 89 |
| RV↔YV | 89 / 89 |
| YV↔AV | 89 / 89 |
| SV↔AV | 86 / 89 |
| RV↔SV | 86 / 89 |
| SV↔YV | 86 / 89 |

**This cell of the matrix is saturated and therefore not discriminating.** With 89
deliberately broad concepts over 20,210 mantras, nearly every concept occurs in every Veda.
That is an honest property of a compact ontology, not a bug — but it means "concepts
bridging two Vedas" is only useful when ranked by *balance* (how evenly a concept is shared)
rather than by presence, which is how the insight query does it.

---

## 6. Cross-Veda parallels

**1,538 identical pairs**, 750 classified `EXACT_PARALLEL_OF` (identical at or above
`SCRIPT_FOLDED`) and 788 `VARIANT_OF` (identical only once word division is dropped).
**3,049 near parallels** above the 0.72 floor. Discovery runs in ~11 s over 20,095
comparable mantras.

Candidate generation is MinHash LSH over **character** 4-grams — not word shingles, because
the Samaveda has no reliable word boundaries. 17,786 candidates were scored out of a
127.8-million-pair product. Recall was validated by brute-forcing the entire 3.64M SV×YV
product: the bands recover 268/268 pairs at Jaccard ≥ 0.44, which is the threshold below
which a pair provably cannot reach the similarity floor.

Similarity is `0.5·ngram_jaccard + 0.5·lcs_ratio`. Token Jaccard and edit ratio are stored
per row but excluded from the blend: token overlap runs 0.2–0.5 even on genuine RV/SV
identities, so a blend including it would systematically under-score exactly the pairs that
matter most.

Sample discoveries, all verified against the stored text:

| | |
|---|---|
| RV 1.1.9 = VSM 3.24 | `sá naḥ piteva sūnáve...` — the close of the Rigveda's first hymn, taken into the Agnihotra |
| RV 1.3.10–12 = VSM 20.84–86 | the three Sarasvatī verses, moved as a block |
| RV 1.22.19 = VSM 6.4 **and** 13.33 | `víṣṇoḥ kármāṇi paśyata` — used twice in the Vājasaneyi |
| RV 1.90.6 = VSM 13.27 | `mádhu vā́tā ṛtāyaté` — the honey verses; `VARIANT_OF`, since VSM prints `mādhvīrnaḥ santvoṣadhīḥ` where RV prints `mādhvīr naḥ santv oṣadhīḥ` |
| RV 10.162.6 = AVS 20.96.16 | `EXACT_PARALLEL_OF` at `SCRIPT_FOLDED` |

That fourth row is worth dwelling on: the two editions have **identical letters in a
different word division**, which is precisely what `VARIANT_OF` exists to say and what a
single `PARALLEL_TO` would have hidden.

---

## 7. Formulas

**4,825 `Formula` nodes, 22,686 `USES_FORMULA` edges** — 27,511 edges in total, against the
**87,296 undirected passage-to-passage edges** the combinatorial modelling would have needed
for the same facts. A 3.2x reduction, and the more important half is that the formula becomes
a first-class queryable entity instead of an implicit property of an edge set. 3,693 formulas
are cross-Veda; **236 occur in all four Vedas**.

The largest hub, `pāta svastibhiḥ`, has 93 occurrences: on its own that is 4,278 passage-pair
edges replaced by 93.

| Veda | formulas | occurrences | mantras covered |
|---|---:|---:|---|
| RV | 4,016 | 9,936 | 5,101 / 10,552 (48.3%) |
| **SV** | 2,010 | 3,112 | **1,319 / 1,844 (71.5%)** |
| YV | 1,633 | 3,069 | 1,207 / 1,975 (61.1%) |
| AV | 2,767 | 6,892 | 2,938 / 5,839 (50.3%) |

The Samaveda has the *highest* formula coverage of the four, which was not a given: a
word-n-gram extractor would have found almost nothing there and silently reported that the
most formulaic of the four Vedas has no formulaic language. The method mines word n-grams
from the word-divided corpora and then detects them by **substring search on the
word-boundary-free surface**, which is what reaches SV. 584 of SV's 3,112 occurrences (19%)
are reachable only that way and are marked with a distinct method and a lower score.

Top cross-Veda formulas, all four Vedas: `pāta svastibhiḥ sadā naḥ` (93 — the standard
hymn-closing "protect us evermore with blessings"), `viśvā bhuvanā` (60, "all beings"),
`parame vyoman` (53, "in the highest heaven"), `brahmaṇas pate` (38).

A rule not in the brief was added and mattered: **9-word probe spans** are mined but never
emitted, so that an 8-word "formula" which is really a chopped-out window of a verse-length
repetition is suppressed rather than promoted. 75% of the 8-word nodes were such windows.
The word-count histogram now decays smoothly (2049/1267/635/350/254/190/146) instead of
spiking at the ceiling, node count fell from 6,000 to 4,825, and coverage *rose*.

---

## 8. Concepts and semantic candidates

**89 `Concept` nodes**, 955 Sanskrit aliases, 254 English aliases, 18 `BROADER_THAN` edges,
101 `DEVATA_ASSOCIATED_WITH` edges. Every Sanskrit alias is attested as a real folded token
in the corpus and every English alias occurs in a translation — enforced by tests, not by
intent. Zero cross-concept alias collisions.

The Devatā/Concept separation is maintained strictly: `VG:CONCEPT:AGNI-FIRE` is ritual and
natural fire, `VG:DEVATA:AGNIH` is the god. They are joined by `DEVATA_ASSOCIATED_WITH` and
are never merged.

**47,542 `ABOUT_CONCEPT` assertions.** (47,754 before adversarial QA removed four
mis-sensing English aliases; see S5 in §12.)

| Veda | mantras | with translation | concept coverage |
|---|---:|---:|---:|
| RV | 10,552 | 99.5% | **96.2%** |
| YV | 1,975 | 96.4% | **92.3%** |
| AV | 5,839 | 83.5% | **82.0%** |
| SV | 1,844 | **0%** | **71.7%** |

Confidence bands do not overlap and the ordering encodes the epistemics: English evidence
0.42–0.58 < SV sandhi-substring 0.55–0.67 < Sanskrit token 0.80–0.92. An English match is a
claim about Griffith's word choice; a Sanskrit match is a claim about the text.

### Independent corroboration of the concept layer

The Devatā↔Concept lift table was never hand-coded — it falls out of matching concept
aliases against passages whose deity comes from the anukramaṇī. Its top rows are exactly
what a Vedicist would predict:

| deity | concept | support | lift |
|---|---|---:|---:|
| Uṣas | dawn | 112 | **10.81** |
| Aśvins | chariot | 137 | 2.85 |
| Agni | fire | 1,157 | 2.55 |
| Soma Pavamāna | soma-drink | 467 | 2.46 |
| Indra | vajra | 182 | 2.19 |

---

## 9. Graph Data Science

GDS **2.13.12** was enabled on the local Neo4j 5.26 Community container and works. Every
algorithm runs at `concurrency: 1` for reproducibility, over a named, versioned projection
of 28,066 nodes and 258,922 relationships, projected **undirected** (a symmetric parallel
stored A→B rather than B→A is an artifact of sorting the pair by key, and left directed it
would bias PageRank toward whichever key sorts later).

Nothing in the pipeline depends on GDS: the deterministic analytics in
`vedagraph.enrich.analytics` are computed in Python, and `run_analytics` returns a reason
rather than raising when the plugin is absent.

**Top PageRank:** triṣṭubh (340), indraḥ (237), gāyatrī (209), **fire (205)**, **heaven
(172)**, **soma juice (168)**, agniḥ (161). Concepts entering the top ten alongside metres
and deities is the enrichment layer showing up in the graph's own structure.

**Communities:** 36 at modularity 0.482 — down from 85 at 0.702 before enrichment. That
drop is the point: `USES_FORMULA` and `ABOUT_CONCEPT` edges connect clusters that were
previously separate, so the graph is genuinely more integrated and less modular than the
bare hierarchy was.

**Bridge mantras** (sampled betweenness, restricted to `:Mantra` — otherwise Mandala
containers dominate by an artifact of `CONTAINS`): AVS 19.23.30, AVS 19.22.21, RV 8.84.3,
RV 4.31.3.

**Node similarity** returns 24 cross-Veda pairs that share neighbours but have **no**
textual parallel — 0 before enrichment. This is the "semantically similar, lexically
different" deliverable, e.g. AVS 3.17.9 ~ VSM 12.70 (0.714).

---

## 10. Evidence-first contract

Every enrichment edge carries ten properties: `trust`, `method`, `score`, `evidence`,
`evidence_count`, `state`, `pipeline_version`, `run_id`, `model`, `prompt_policy`. The
`why_are_these_connected` query returns all of them for one edge, with no second lookup and
no join — the "why are these connected?" click is answerable from the edge alone.

`Provenance` enforces the contract at construction, not at review time:

- an edge with no evidence cannot be built;
- a score outside [0, 1] cannot be built;
- `LLM_EXTRACTED` **cannot** be written with `state=ACCEPTED` — the policy that model
  output never becomes canonical is a type error, not a convention;
- a model id is required on an LLM row and forbidden on a deterministic one, in both
  directions.

---

## 11. Semantic candidates

**736 candidate assertions over 364 passages**, every one `LLM_EXTRACTED` / `CANDIDATE`,
with a model id, a prompt-policy version, a packet digest and a verbatim evidence quote.
None can be `ACCEPTED`: `Provenance` refuses that combination at construction.

The stage is split so the non-determinism is contained. `--emit-packets` selects passages
and freezes exactly what the model may see; the model reads them; `--ingest` validates what
came back. Only the middle step is non-deterministic, and nothing hides it inside a build.

Selection is deterministic and prioritises passages with a translation, a cross-Veda
parallel, and a non-Rigvedic source. It chose **228 Yajurveda and 172 Atharvaveda** packets
and no Rigveda at all — correctly, since the Rigveda already has its own semantic pilot.

| predicate | edges | | predicate | edges |
|---|---:|---|---|---:|
| DESCRIBES | 280 | | INVOLVES_OFFERING | 14 |
| INVOKES | 222 | | INVOLVES_RITUAL | 11 |
| REQUESTS | 109 | | HAS_THEME, CONTRASTS_WITH | 8 each |
| PRAISES | 38 | | REFERS_TO_*, INVOLVES_SUBSTANCE | 11 |
| DESCRIBES_ACTION | 35 | | | |

### The finding that gives this layer its value

**All 400 packets carry an empty `devatas`, `rishis` and `chandas` list.** Only the Rigveda
has an anukramaṇī in this corpus, so the deterministic traditional-metadata layer has *zero*
coverage on the Atharvaveda and Yajurveda. Every one of the 382 deity edges is therefore
net-new, including relations the concept layer structurally cannot express: the dual and
collective deities (Indrāgnī, Indrāsomau, Mitrāvaruṇau, Dyāvāpṛthivyau, Uṣāsānaktā) and the
object-deities AV/YV ritual actually addresses — `DUNDUBHIH` the drum, `DHANUH` the bow,
`JYA` the bowstring, `VARMA` the armour, `YUPAH` the sacrificial post, `GRAVANAH` the
pressing stones.

### Three proposals struck by hand

The model proposed `DESCRIBES → VG:DEVATA:KAH` for the refrain *kásmai devā́ya havíṣā
vidhema* in AVS 4.2.7, VSM 32.6 and 32.7, flagging it itself as a judgement call. The quotes
are "to what god may we pay worship?" and "What God shall we adore with our oblation?" — the
verse *asks* which god. Treating that as describing a deity named Ka imports a later
reification, rests on the anukramaṇī rather than the text, and AV/YV have no anukramaṇī here
to rest on. Struck, consistent with ADR-013 and with the frozen ontology's refusal of
`IS_GOD_OF`.

### What the model could not say, and why that is a deliverable

The extraction returned a measured list of objects it wanted to assert and could not,
because no node exists. This is a concrete, evidence-backed brief for a v2 ontology rather
than a vague "add more concepts":

- **Deities:** Prajāpati (AVS 7.80 addresses him by name — the single largest gap), Bhaga,
  Aryaman, the Vasus as a class, Nārāśaṁsa, Mātariśvan, Vivasvant, Trita, Purandhi,
  Gandharva/Apsaras, Aja Ekapad (whose standing pair Ahi Budhnya *does* have a node),
  Amāvāsyā (Sinīvālī and Rākā have nodes; the new moon does not), and the Aṅgirases,
  Atharvans and Bhṛgus as distinct ancestral families rather than collapsed into `PITARAH`.
- **Concepts:** sleep, marriage/co-wife, fear, cremation, Aśvamedha, the vedi, the goat,
  brahmodya as a form, the varṇa terms, and the unity of the gods (*ekaṁ sat*).

Two whole hymns produced zero output solely for want of a "sleep" concept: AVS 4.5 is a
sleep charm end to end. Eleven more packets were Griffith cross-reference stubs ("Repeated
from XII. 56.") with no translated text and should be excluded from selection next time —
they burned 11 of a 400-passage budget.

---

## 12. Adversarial QA

Full report: [GRAPH_ENRICHMENT_V1_ADVERSARIAL_QA.md](GRAPH_ENRICHMENT_V1_ADVERSARIAL_QA.md).

Agent G attacked eight surfaces and found **one BLOCKER and five SERIOUS defects**. All are
fixed in this release, and each fix is verified by measurement rather than by inspection.

### B1 — private-use sentinels in published evidence (BLOCKER, fixed)

`fold_transcription` maps ṛ, ṝ, ḷ and ṃ onto private-use code points U+E000–U+E003 so that
IAST and ISO 15919 spellings compare equal. Those code points are unassigned: a comparison
device that must never reach a person. They were reaching people, in **88.6% of parallel
rows and 31.9% of concept assertions**, and the damage was invisible because an unassigned
code point usually renders as nothing — `pṛñcatīr` published as `pñcatīr`, and `ṛtasya` as
`tasya`, which is a different Sanskrit word. Evidence that silently misquotes the text is
worse than no evidence, because it looks checkable.

Fixed by promoting the renderer the formula stage already had into shared
`surfaces.render_for_display`, applying it at the single funnel each stage publishes
through, and adding `published_text_is_free_of_private_use_code_points` to validation.
Verified live: **0 of 76,499 enrichment edges** carry an unassigned code point, along with 0
of 4,825 Formula display forms and 0 of 178 Concept labels.

### S1 — `match_level` claimed an identity that did not hold (fixed)

4,229 of 6,271 rows published `match_level: SANDHI_INSENSITIVE` while their own
`levels_reached` was empty — asserting that two texts are identical at a level where they
demonstrably are not, and inflating the manifest's identity tally from 2,042 to 5,432.
`match_level` is now an identity claim and is empty for a near parallel; the surface a pair
was scored on lives on the evidence span, where it belongs.

### S3 — the visarga fold, again, in the formula display path (fixed)

The same defect Agent B found in `surfaces.py`, in a second place: `formulas._build_views`
transliterated before folding, so 1,305 tokens across 824 mantras lost their visarga on the
display surface. 303 formula evidence quotes misquoted their own passage, and `pataye namo
nama(ḥ)` split into two nodes printing an identical `display_form`. Fixed and measured: **0
of 1,135 sampled quotes** now fail to resolve on the surface they name, and **0 duplicate
display forms** remain.

### S4 — the concept cap's tie-break was the alphabet (fixed)

The scoring bands are coarse, so equally-scored concepts tie exactly and the tie-break
decided the outcome on **80.1% of capped passages**. Breaking it on the concept id meant the
alphabet decided: kept concepts averaged alphabetical rank 27.8 of 89, dropped ones 60.0,
and YAJNA-SACRIFICE was dropped 425 times and STOMA-PRAISE 380 times for no reason but their
initial letter. The tie-break is now corpus-wide rarity — of two equally-scored concepts,
the one attested on fewer passages says more about this passage — with the id retained as
the final key so the result stays deterministic.

### S5 — structured alias errors that random sampling cannot find (fixed)

Four English aliases were wrong in a *patterned* way. Measured against the passages they
matched: `realm` → RAJAN-KINGSHIP wrong **82.9%** ("the realm of the gods", "Yama's realm");
`stone` → ASMAN wrong ~**62%** ("make thyself a stone"); `way` **23%** adverbial ("turners
this way"); `bow` **21%** verbal ("let the four directions bow to me"). All four removed
with their measurements recorded in the registry. The Sanskrit aliases are kept, so each
concept survives with better precision rather than being dropped. `ASMAN-PRESSING-STONE` was
also relabelled to "stone", because its definition always covered stone generally and the
narrow label was the defect rather than the matches.

### S2 — `EXACT_PARALLEL_OF` is shared with the lexical layer (documented, by design)

The live graph holds 1,006 `EXACT_PARALLEL_OF` edges, not 750: 256 are the pre-existing
within-Rigveda lexical edges, which carry no `pipeline_version`, no `run_id` and no
evidence. That is the documented design — `pipeline_version` is inside the `MERGE` pattern
precisely so the two layers cannot overwrite each other — but any query counting this type
must filter on it.

### The methodological finding, which matters more than any single defect

Agent G's own independent random sample of 60 concept assertions returned **97.8% loose /
97.7% strict**, reproducing Agent D's loose figure and *beating* its strict one. Both
numbers are real and both are nearly useless: a 60-row draw has roughly a 4% chance of
containing a single `realm` row. The errors in this layer are concentrated in a handful of
aliases, not spread across rows, so **concept precision must be reported per alias, not per
row** — and the per-alias audit is what found S5. Recorded here as a standing instruction
for the next release.

### Attacks that found nothing

Worth stating, because a clean attack is evidence: 60/60 near parallels judged correct
across all three score bands including the 0.72 floor; **zero refrain collisions** in an
exhaustive longest-common-substring test over all 3,049 near parallels; **1,538 of 1,538**
identity claims verified mechanically against the stored text; the RV↔SV sandhi worry tested
directly and not reproduced; all five artifacts bit-reproducible on a full re-run; every cap
binding exactly; **0 missing and 0 extra** across 76,711 edges compared artifact-to-live;
base graph counts, both corrected Griffith translations, and the duplicate-key check all
correct.

### Open findings carried as backlog

MINOR and COSMETIC items not fixed here, all measured and recorded in the QA report: 22.9%
formula node redundancy after maximality (1,103 strict substrings survive); 34 formulas
display an avagraha-truncated non-word, because `vedagraph.normalize` treats the apostrophe
as a separator and GRETIL's `jātavedó 'gne` tokenises to a bare `gne` — an upstream
normalization fact rather than a formulas defect; `notes` is dropped when `ABOUT_CONCEPT` is
projected, so alias provenance is artifact-only; and one base-corpus OCR error in Griffith
RV 9.86.32 ("as he knows **bow**" for "as he knows how") that the English path amplified.

---

## 13. Decision

**`VEDAGRAPH_GRAPH_ENRICHMENT_V1_READY`**

Every gate is green, the one blocker is fixed and verified in the live store, and the
remaining findings are measured, documented and non-blocking.

| gate | result |
|---|---|
| pytest | 1,246 passed, 42 skipped (pre-existing: absent AV scan, uninstalled `openai`, live-DB test) |
| ruff | clean |
| mypy strict | clean, 134 source files |
| Offline invariants | 26 checks, 0 findings |
| Live invariants | 12 checks, 0 findings |
| Insight queries | 25/25 pass, all under 300 ms |
| Determinism | 5/5 artifacts byte-identical across two full builds |
| Load integrity | 0 unmatched, 0 duplicate rows, 0 missing/extra across 76,711 edges |
| Evidence integrity | 0 of 76,499 enrichment edges carry an unassigned code point |
| Semantic freeze | intact — 22 tests pass, sealed corpus byte-identical |

Trust census, read from the live graph: **76,499 `DETERMINISTIC_DERIVED` / `ACCEPTED`**,
**736 `LLM_EXTRACTED` / `CANDIDATE`**, **119 `SOURCE_EXPLICIT` / `ACCEPTED`**. No model
output is accepted anywhere, and the type system is what guarantees it.

`NEXT_PROJECT_PHASE = FASTAPI_SEARCH_AND_GRAPH_API`

### Remaining enrichment backlog

1. **A v2 concept ontology**, driven by the measured gap list in §11 — Prajāpati, Bhaga,
   Aryaman, the Vasus, Gandharva/Apsaras; sleep, marriage, fear, cremation, Aśvamedha.
2. **Per-alias precision auditing** as the standing method, replacing per-row sampling.
3. **Formula redundancy**: 1,103 surviving formulas are strict substrings of another.
4. **The avagraha residual** in `vedagraph.normalize`, which needs a notation-aware fold
   rather than a bigger table, and is a contract change rather than a patch.
5. **Fold the two overlays into their real homes** — `infra/requirements-graph.txt` and
   `data/registry/upstream_corrections.yaml` — in the same change that legitimately
   reissues the semantic freeze.
6. **`SHARES_FORMULA_WITH`** is declared and deliberately unmaterialised; if a consumer
   needs it as an edge rather than a two-hop traversal, it needs a selectivity threshold
   first.
7. **Human review** of the 736 semantic candidates, none of which may be accepted without
   it.
8. **Exclude Griffith cross-reference stubs** from semantic packet selection.


> **R5 correction.** The Samaveda now carries 173 `HAS_TRANSLATION` edges, every one a
> `REUSED_RENDERING` of Griffith's Rigvedic English on verified character-identical
> Sanskrit. Its count of INDEPENDENT Samavedic English translations is still 0, which is
> what the sentence above was reaching for; `GAP-TRANSLATION-004` types the distinction per
> verse so no total can report 173 as the Samaveda's own English.
