# V3.1 Wave 2 — ritual/offering depth, the hotar type error, and measured rite recall

**Agent:** E · **Assignments:** fix 2 (XS item, Q90), fix 6 (Q56, Q84, Q100), fix 7 rite
half (Q13, Q60) · **Timebox:** ~90 min, overrun on the idempotence defect in §6

| Q | Claim | Basis |
|---|---|---|
| **90** | **CLEARED** | hotṛ now heads the priestly-role table; 3 `PERFORMED_BY` edges; alias contamination measured and published |
| **13** | **CLEARED** | measured recall 9.93% is a column on the rite node, not a caveat |
| **60** | **CLEARED** | distinct passages per side (41/41) + recall now available in the row; cross-product disclosed |
| **100** | **NOT cleared — materially improved** | `Offering` 2 → 8, join 5 → 32 rows; criterion demands "order hundreds" and the binding dimension is now `HumanConcern` = 7 |
| **56** | **NOT cleared — CUT** | needs new `Ritual` nodes with read-verse evidence; see §7 |
| **84** | **NOT cleared — CUT** | needs a passage-level ritual-context property; see §7 |

Q71 was listed under fix 7 but its per-question entry assigns it to `AGENT_D_RISHI_MATERIAL`
(material-culture alias recall). Not touched.

---

## 1. Node and edge counts, before and after

| | before | after |
|---|---|---|
| `RitualRole` nodes | 10 | **11** |
| `Offering` nodes | 2 | **8** |
| `Ritual` nodes | 8 | 8 (unchanged — see §7) |
| `SocialRite` nodes | 5 | 5 |
| `PERFORMED_BY` | 16 | **19** |
| `USED_FOR_RITE` — `PER_PASSAGE` (strict) | 110 | **110** (untouched, by design) |
| `USED_FOR_RITE` — `CONTAINER_INHERITED` (new prior layer) | 0 | **419** |
| Relationships, total | 266,347 | **266,769** (+422 = 3 + 419) |
| Nodes, total | 108,776 | 108,777 (+1, another agent's) |
| Edges with no `quality_tier` | 0 | **0** |

`sent=12 landed=12`. Idempotent: runs 3 and 4 both end at 266,769 with zero drift, 419
stable priors and zero swept.

## 2. Q90 — the hotar. Cleared, and it was two defects, not one

**A conflict, reported as instructed.** Another agent had already retyped
`VG:CONCEPT:HOTR-PRIEST` to `node_type: RITUAL_ROLE` in `concepts.yaml` by the time I got
there. I did not redo it. But the retype alone was **half the fix**, and the missing half
was the one `rituals_v3.yaml` explicitly warned must not be deferred.

**This fix was already written down in the repository.** `rituals_v3.yaml` closes with "The
PERFORMED_BY note, which is this layer's one real blocker":

> The hotar is the officiant this corpus names most … and he appears in no `PERFORMED_BY`
> edge in either `rituals.yaml` or this file. That is not an evidential gap. **It is a type
> error one field wide.** … The fix is: `concepts.yaml`, `VG:CONCEPT:HOTR-PRIEST`:
> `node_type: CONCEPT -> RITUAL_ROLE`, and then adding it to the `performed_by` of
> SAUTRAMANI (VS 21.30, 21.31, 21.58), GRAHA-SOMA-DRAWING (RV 2.37.1) and YAJNA-SACRIFICE
> (RV 2.1.2, RV 1.94.6).

All three officiant edges now exist, and **every verse behind them is that file's own**,
read by its author under its own read-the-verse rule. This pass added no verse and imported
nothing.

**Verified live** — the priestly-role table, top four:

| role | mentions | alias purity |
|---|---:|---:|
| **priest (hotṛ)** | **321** | **0.9221** |
| sacrificer (yajamāna) | 94 | 1.0 |
| brahman priest | 67 | 1.0 |
| adhvaryu | 24 | 1.0 |

`(:Ritual)-[:PERFORMED_BY]->(hotṛ)` returns soma cup drawing (graha), sautrāmaṇī, and
sacrifice (yajña).

### 2.1 A defect the brief did not know about: the 321 is 7.8% the wrong office

The coordinator asked me to verify the 321 first. I did, **per alias rather than per row**,
because a row-level sample in this repository once read 97% while one alias was 82.9% wrong:

| alias | edges | office |
|---|---:|---|
| hotā · hotāraṃ · hotāram · hotur · hotre · hotrāt | 213 · 45 · 37 · 3 · 3 · 1 | the hotar |
| **adhvaryo · adhvaryavaḥ · adhvaryuḥ** | **9 · 4 · 1 = 14** | **the ADHVARYU** |
| **ṛtvijam · ṛtvijaḥ** | **7 · 4 = 11** | **any officiant** |

So the node's alias list was a portmanteau of three offices, and `rituals_v3.yaml` had
already flagged it: *"Retyping the node without splitting it produces a RitualRole that
answers 'which rites does the adhvaryu officiate at' twice, differently."* Retyping without
splitting — which is where the tree stood when I arrived — creates that exact double answer.

Fixed in the artifacts: `adhvaryuḥ, adhvaryavaḥ, adhvaryo` moved to
`VG:CONCEPT:ADHVARYU-PRIEST` (a `RITUAL_ROLE` already, holding none of the three, so no
folded surface collides). `ṛtvijam, ṛtvijaḥ` **withdrawn with no replacement node**: ṛtvij-
is any officiant, and minting a generic-officiant node would enter it into the very
priestly-role census Q90 is about as a competing office — the same reasoning the diagnosis
applies to `sindhu`, the generic word for "river", in a hydronym table. Recorded as backlog:
a generic office needs an `is_generic_office` flag and a query default that excludes it.

**Live measured purity: 0.9221** (296 own / 321 total / 25 foreign). The artifact declared
302; the loader recomputed 296, because an edge matching two aliases is one edge. The
loader's figure wins and the artifact was corrected to it.

**What I did not do, and why.** I did not rewrite the 25 `MENTIONS_ENTITY` edges. The
mention layer is built from the registry by `scripts/build_domain_v2.py`; the alias split
lands there on the next run of that builder. Rewriting them from a V3 loader would put two
code paths in charge of one layer's edges, which with several passes sharing one database is
how two conventions get established for one fact. **The corrected figure is published
instead of imposed** — `alias_purity`, `mention_edges_own_alias` and
`mention_edges_foreign_alias` are now node properties, so the role query can return the
office's own count and its purity in the row. **Action for the coordinator: the live edge
correction needs one `build_domain_v2.py` run, which I did not take because it re-projects
Agents C and D's layers too.**

## 3. Q100 — `Offering` 2 → 8. Improved, not cleared

The diagnosis named the fix precisely: *"the `INVOLVES_OFFERING` predicate already reaches
ghṛta, anna, paśu, aśva, go, soma — those targets are typed `Substance`, not `Offering`,
which is the whole defect."* So this is a **typing pass, not an acquisition**. Every label
comes from a witness already in the graph, and the loader **recomputes each witness and
refuses to label without it** (`unwitnessed: []` on every run):

| node | taxonomic (`broader: havis`) | `INVOLVES_OFFERING` edges | witnesses |
|---|:-:|---:|---:|
| ghṛta | yes | 3 | **2** |
| soma | yes | 2 | **2** |
| anna | no | 1 | 1 |
| go | no | 1 | 1 |
| paśu | no | 1 | 1 |
| aśva | no | 1 | 1 |

The label is **added, never substituted**: ghṛta stays `:Substance`, go stays `:Animal`.
Substituting would have broken `USES_SUBSTANCE` — the mirror of the error being fixed. A
test enforces that every row keeps its material label. `witness_count` is stored per node so
a consumer can see that ghṛta has two witnesses and aśva has one.

**Result:** the four-dimension join goes from **5 rows / 3 passages** to **32 rows / 22
passages / 8 offerings** — 6.4×. The criterion demands "order hundreds of rows", so **Q100
is not cleared.** The binding dimension is now `HumanConcern` at **7 nodes** with 326
`ADDRESSES_CONCERN` edges, which the diagnosis also assigns to me and which I did not reach.
The loader reports `class_is_complete: false` and a completeness note on every run, so a low
row count through this class cannot be read as a small phenomenon — which is the criterion's
other requirement and is met.

**Refused, with reasons:** puroḍāśa (the rice-cake oblation), madhu, payas, dadhi, tila.
Each is a plausible Vedic oblation; none has an entity node or any witness in this
repository. Naming them from general knowledge of the ritual tradition is exactly what
"import no external ritual manual" forbids.

## 4. Q13 / Q60 — measured rite recall. Cleared

**The measured rite-layer recall figure, as asked:**

| rite | locus | tagged | book size | **strict recall** | enrichment |
|---|---|---:|---:|---:|---:|
| marriage (vivāha) | AV K14 | 14 | 141 | **9.93%** | **58.21×** |
| house building (śālā) | AV K09 | 19 | 311 | **6.11%** | **34.87×** |

These are node properties (`strict_recall_against_locus`, `locus_book_passages`,
`locus_tagged_passages`, `locus_enrichment`, `recall_is_measured`), so a query returns them
**as columns**. That is the whole point: the reader who runs the obvious query never sees a
caveat.

### 4.1 The design decision: I refused to tag the locus book, and that is the fix

The obvious move is to tag all 141 K14 passages as marriage verses. **Refused.** It would
make recall against K14 exactly 100% *by construction* — a circular measurement that
destroys the only honest number on the table — and it would assert of 127 individual verses
something no source in this repository says.

So the strict verse-level layer is left **completely alone** (110 edges, before and after),
its recall is computed and published, and the book-level prior is projected as a **separate
`CONTAINER_INHERITED` / `TIER_D` / `CANDIDATE` layer** (419 edges). A reader filtering to
`PER_PASSAGE` never sees a prior. This is precisely how the graph already carries the
Anukramaṇī's sūkta-wide deity labels rather than pretending they are per-verse.

### 4.2 The locus is measured from the graph, and I refused the brief's K18

The diagnosis suggests seeding from "the AV's own kāṇḍa structure (K14 = marriage, K18 =
funerary)". K14 is **confirmed by the graph's own tag distribution** — 14 of the AV's 25
marriage tags fall in one kāṇḍa of 141 verses out of 6,590, a 58-fold enrichment — so the
prior needs no external authority.

**K18 = funerary is REFUSED.** Of 9 AV funerary tags, K18 holds **one**, against 2 in K15
and 2 in K05. Enrichment ≈ 0.8×, i.e. K18 is very slightly *depleted*. That the
Atharvaveda's eighteenth kāṇḍa is its funeral book is a true statement about the
Atharvaveda and **it is not a statement this repository's data makes** — seeding from it
would be importing outside knowledge under cover of a measurement. Recorded as a real gap:
either the funerary alias list has ~1/20th the recall of the marriage one, or the tagger
misses K18 systematically. Both deserve a pass; neither is this pass's to guess.

Also refused: sabhā (12 tags over 10 kāṇḍas, no locus — correct for a rite that is an
occasion, not a book) and sūṣā/K01 (41× enriched but K01 is the AV's opening miscellany, so
6 verses clustering is not a book's subject; accepting it would assert 189 childbirth verses
on the strength of six).

Two thresholds are chosen (`RITE_LOCUS_MIN_ENRICHMENT = 20.0`,
`RITE_LOCUS_MIN_TAGGED = 5`), declared as module constants, and **everything resting on them
is `TIER_D` for that reason alone** — the same grading rule this module applies to the four
similarity-derived formula `VARIANT` rows.

### 4.3 Q60's cross-product, measured

The 788 `vivāha` pairs are the cross-product. Measured now on the strict layer: **800 raw
pairs from 41 distinct passages per side**, with `recall = 0.0993` available on the rite
node. The honest row is 41 and 41 with a 9.93% recall attached, not 800 — and the raw pair
count is now derivable *alongside* the distinct counts rather than instead of them. The
query change is Agent A's; see §8.

## 5. Artifacts, loader, registration, tests

| file | change |
|---|---|
| `data/domain/vedagraph_domain_v2/ritual_depth_v3_1.yaml` | **new**, 3 blocks, every entry carrying a `witness`, a `basis` and a `QUESTION_UNLOCKED`; every refusal written down |
| `data/registry/concepts.yaml` | hotṛ alias list split (retype was another agent's) |
| `data/domain/vedagraph_domain_v2/domain_entities_material.yaml` | 3 adhvaryu forms received |
| `src/vedagraph/domain/v3_loader.py` | `load_ritual_depth` + 5 helpers; `RITE_LOCUS_MIN_*` and `_RITE_PRIOR_GRADE` constants |
| `scripts/build_knowledge_model_v3.py` | `ritual_depth` layer registered in `LAYERS` and `steps`, with its run-order constraint |
| `tests/domain/test_v3_1_formula_and_assertion.py` | +9 tests (5 offline, 4 live) |

**The loader disbelieves the artifact.** Every `witness` is a claim to be *checked*: a
declaration whose witness is not in the graph produces no label and is reported under
`unwitnessed`. A curated typing file's characteristic failure is a plausible entry nobody
re-measured, and the only defence is to make the loader refuse to take the file's word.

**Gates:** `ruff check` clean · `mypy --strict` clean (159 files) · **23/23** of my module
pass live, 16 offline + 7 skipped · `tests/domain/` regression **196 passed, 24 skipped, 0
failed**.

## 6. A defect I introduced and caught: the layer was not idempotent

Worth recording because the second run is what found it and the first run looked perfect.

`_apply_rite_loci` counted **all** `USED_FOR_RITE` edges when measuring, including the
priors it had written on the previous run. On run 2, `tagged_in_book` for vivāha read **141
of 141** and the recall figure this layer exists to publish read **100%** — the exact
circularity §4.1 was designed to avoid, reintroduced through the back door. And because the
prior `MERGE` was unkeyed, it matched the previous run's edge, so the sweep then deleted all
419: the layer oscillated between 419 edges and 0.

Two fixes, both now covered by a live test:
1. The measurement counts **only** `attribution_precision = 'PER_PASSAGE'`. The prior must
   never be its own denominator.
2. The prior is `MERGE`d **keyed on its derivation** —
   `MERGE (p)-[r:USED_FOR_RITE {derivation: 'BOOK_LOCUS_PRIOR'}]->(s)` — so a prior is a
   distinct edge from a strict tag and can never absorb one.

Verified: runs 3 and 4 both leave 266,769 relationships, 419 stable priors, 0 swept, 110
strict edges untouched, recall stable at 9.93% / 6.11%, and `declared_vs_live_drift: []`.

**The drift detector also caught my own artifact twice**, which is the mechanism working:
K09 was declared 312 verse-passages and is 311, and the hotar's own-alias total was declared
302 and measures 296. Both corrected to the live figures.

## 7. Cut, with reasons — Q56 and Q84

Cut per the coordinator's instruction to cut fix 6's long tail. Both are real and neither is
blocked; they are the expensive half.

**Q56 (rite inventory).** Needs `vājapeya`, `rājasūya`, `darśapūrṇamāsa` and `cāturmāsya`
as `Ritual` nodes. Not done, and the reason is the artifact discipline rather than the clock
alone: `domain_entities_ritual_v3.yaml`'s rule is that *"every Sanskrit alias below was
probed against all 20,210 mantras … and then READ … in the verse that produced the hit. A
probe count with no read verse is not evidence and is not in this file."* Four rites is four
alias probes and every hit read, which is a session's work, not a tail. **Rites left
unmodelled: vājapeya, rājasūya, darśapūrṇamāsa, cāturmāsya** — and the aśvamedha, which
*is* a node, still has 2 apparatus edges for the rite occupying VSM 22–25. The mandatory
mitigation the diagnosis names — an `inventory_coverage` column so a low rank cannot read as
low apparatus — is a query change and is in §8.

**Q84 (passage-level ritual context).** Not done. I had planned to fold it into the same
book-locus machinery — AV kāṇḍa → rite context, YV adhyāya → ritual context — and the
locus threshold work consumed the budget instead. The machinery now exists and is generic:
`_apply_rite_loci` takes `(veda, book, rite)` and would extend to YV adhyāyas against the
`described_in` distributions already in `rituals_v3.yaml`. Recommended as the cheapest next
ritual item. Until it exists, the diagnosis is right that **the context column must be
omitted, not filled with `false`** — which is a query change, §8.

## 8. Written spec for Agent A (`queries.py` is yours)

1. **`ritual_roles`** — return `alias_purity`, `mention_edges_own_alias` and
   `mention_edges_foreign_alias` from the `RitualRole` node as columns. hotṛ's 321 is 7.8%
   another office; a table printing 321 unqualified is wrong in favour of the office this
   pass just promoted.
2. **`passages_used_for_a_rite` / `social_rites`** — default to
   `r.attribution_precision = 'PER_PASSAGE'`, and return `strict_recall_against_locus`,
   `locus_book`, `locus_tagged_passages` and `locus_book_passages` as columns. Offer the
   419 `CONTAINER_INHERITED` priors only under an explicit opt-in, labelled as the book's
   claim. Per the criterion: a rite query whose recall is under a stated floor must return
   the recall figure or refuse.
3. **Q60 rite self-join** — return `distinct_passages_side_a`, `distinct_passages_side_b`
   and the recall; if the raw pair count is returned at all, label it
   `cross_product_pairs` beside them. Measured today: 800 raw / 41 / 41 / 9.93%.
4. **Q100 four-dimension join** — emit a per-dimension coverage row: `Offering` 8
   (`class_is_complete: false`), `HumanConcern` 7, `ADDRESSES_CONCERN` 326. 32 rows is not
   "hundreds" and the row set must say why.
5. **Q56 `ritual_profile`** — add `inventory_coverage`: `Ritual` = 8 nodes against a corpus
   naming considerably more, so a rank is a rank within 8.

## 9. Housekeeping

Both items acknowledged, nothing done: I did **not** mass-reformat (your 26-file
`ruff format` count supersedes my 22 — mine was measured on the working tree mid-session,
yours at the starting commit, and yours is the right number to report), and I made no
`attribution_precision` change to the formula twins. Confirmed live: 0 edges in the graph
lack `quality_tier`.
