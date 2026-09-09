# Atharvaveda concern model V3: the mis-typings, and fever as a connected evidence graph

**Scope.** Two jobs. First, verify and fix four registry mis-typings that an independent
evaluator measured as the single largest blocker in the 100-question benchmark — 15
questions. Second, deepen the Atharvavedic concern model far enough that *"what does the
Atharvaveda say about fever?"* returns a connected evidence graph rather than a keyword
hit list.

**Deliverables.** Two new merge fragments and this report. No existing file was edited, no
code was changed, nothing was written to the graph.

| Artifact | Contents |
|---|---|
| `data/domain/vedagraph_domain_v2/domain_entities_concern_v3.yaml` | 41 new entities, 1 full replacement, 3 declared re-types, 10 recorded refusals, 5 required sandhi suppressions |
| `data/domain/vedagraph_domain_v2/concern_predicates_v3.yaml` | 32 new predicate memberships, 1 promotion, 17 deliberate non-memberships |
| this file | verification with live numbers, the full alias table with every rejection, the fever worked example, the Sarasvatī decision, and the closing caution |

**Merge, dry-run.** Base registry 89 + material 45 + concern V1 29 + V3 41 = **204
entities** against `MAX_CONCEPT_NODES` 260. The real `load_concepts` was run over the
merged document in a scratch tree: **accepted, 204 entities, 0 duplicate ids, 0 alias
collisions, 0 unknown node types, 0 dangling `broader` targets.** Predicate endpoints were
checked against `RELATIONSHIP_SIGNATURES` with the re-types applied: **0 endpoint
violations.**

---

## 1. The four mis-typings

All four verified against the live graph before anything was authored. The queries are in
this report so each can be re-run.

### 1.1 `takman` folded into a `State`-labelled `yakṣma` — **VERIFIED**

```cypher
MATCH (n:DomainEntity {concept_id:'VG:CONCEPT:YAKSMA-DISEASE'})
RETURN labels(n), n.node_type, n.aliases_sa
```
returns

```
labels    : ["Concept","DomainEntity","State"]
node_type : "STATE"
aliases_sa: ["amīvā","amīvāḥ","rapaḥ","takman","takmā","takmānam",
             "yakṣmam","yakṣmaḥ","yakṣmaṃ","yakṣmo"]
```

Four distinct afflictions on one node, labelled with the name of one of them, and typed
`State`, which takes **none** of the four concern predicates: `TREATS` and
`PROTECTS_FROM` have range `Condition` and `{Condition, HumanConcern}`. Measured
consequence: of the 33 mantras that carry a `takman-` form, **15 reach the graph as
"disease (yakṣma)"**, 8 carry no domain-entity mention at all, and **0** carry any
affliction edge. "What does the Atharvaveda say about fever?" is unanswerable, exactly as
reported.

**The V1 refusal, and why it was reversible.** `domain_entities_concern.yaml` records a
deliberate decision not to split, on the ground that a sibling built on the *unclaimed*
`takman-` remainder would hold ~39% of the evidence while carrying the label "fever". That
arithmetic was correct. The premise was that the split had to be made on the remainder. It
does not have to be: the whole paradigm can move, and V3 moves it.

**Measured, by enumerating every folded token beginning `takman-`/`takmā-`:**

| | |
|---|---|
| distinct forms | 10 |
| occurrences | 36 |
| distinct mantras | 33 |
| Atharvaveda | 33 of 33 (RV 0, SV 0, YV 0) |
| rejections | **0** — all 36 are Whitney's "fever" |
| hymns | 12: AVS 5.22 (13 mantras), 1.25 (4), 5.4 (3), 6.20 (3), 11.2 (2), 19.39 (2), and one each in 4.9, 5.30, 9.8, 11.4, 12.5, 19.34 |

Two witnesses that the corpus itself keeps takman and yakṣma apart — neither is an
inference:

1. **They occur side by side, contrasted, in one line.**
   AVS 5.4.9 — "both do thou efface all *yákṣma*, and do thou make the fever sapless."
   AVS 5.30.16 — "by it I have exorcised the *yákṣma* and the hundred pangs of the fever."
2. **The Anukramaṇī indexed them separately.** The deity ascription on the whole of
   AVS 5.22 is `VG:ASCRIPTION:AV:TAKMANACANADEVATYAM-7B6D`, *takmanāçanadevatyam*,
   "having fever-destruction as its deity" — a different ascription from the
   *yakṣmanāçana-* ones on AVS 1.25 and 6.20.

**The fix: four `Condition` entities where there was one `State`.**

| entity | aliases | occurrences | distribution |
|---|---|---|---|
| `VG:CONCEPT:TAKMAN-FEVER` | 10 | 36 | AV 33 / 33 mantras |
| `VG:CONCEPT:YAKSMA-DISEASE` (replaced) | 18 | 92 in 88 mantras | AV 73, RV 14, YV 5 |
| `VG:CONCEPT:AMIVA-AFFLICTION` | 9 | 31 | AV 10, RV 18, YV 3 |
| `VG:CONCEPT:RAPAS-BODILY-HURT` | 4 | 18 | AV 4, RV 12, YV 2 |

The `yakṣma` replacement also *gains* two compounds the V1 alias set had missed:
`rājayakṣma` "royal yakṣma" (AVS 3.11.1, 11.3.39, 12.5.22; RV 10.161.1) and
`ajñātayakṣma` "unknown yakṣma" (AVS 3.11.1, 20.96.6; RV 10.161.1). The split makes the
node *more* complete, not smaller.

**What the old node's edges should become.** Live in-edge counts on
`VG:CONCEPT:YAKSMA-DISEASE`: `MENTIONS_ENTITY` 92, `ABOUT_CONCEPT` 180, `DESCRIBES` 3.

- **`MENTIONS_ENTITY` (92) and `ABOUT_CONCEPT` (180): regenerate, do not repoint.** Both
  are derived from alias matches, so re-running the concept enrichment against the
  replaced registry splits them four ways by construction. Repointing them by hand means
  guessing which alias produced which edge, and `r.derived_from_mention` is the only thing
  that records it.
- **`DESCRIBES` (3): re-read individually.** These were authored, not derived. A rite
  described as being about "disease" is about *yakṣma* unless its passage carries a
  `takman-` form, and none of the three does.
- **`BROADER_THAN`:** the seven V1 children (jaundice, kṣetriya, balāsa, viṣkandha, grāhi,
  āsrāva, kāsa) all stay under `YAKSMA-DISEASE`. Eleven more are added under it by V3.
  `TAKMAN-FEVER` takes **no** parent: fever is not a kind of consumption, and filing it
  under one would restore the fold through the taxonomy having removed it from the node.
- **`DEVATA_ASSOCIATED_WITH`:** `VG:DEVATA:YAKSMANASANAH` exists in the graph, display
  label "the destruction of consumption". It **stays on `YAKSMA-DISEASE` and is not
  copied to `TAKMAN-FEVER`** — consumption-destruction is not fever-destruction, and
  copying it would re-create the conflation one layer up. `TAKMAN-FEVER` therefore takes
  `related_devatas: []`. The honest target, *takmanāçanadevatyam*, is a
  `DEVATA_ASCRIPTION` row in `data/registry/devata_ascriptions_av.yaml` and is not a
  `Devata` node; measured, **the Atharvaveda has 0 `HAS_DEVATA` edges in the live graph.**

### 1.2 Sarasvatī is not typed `River` — **VERIFIED**, and the decision is now **YES**

Full evidence in §3, because it needed a re-measurement rather than a one-line fix.
`MATCH (n:River) RETURN n.display_label` returns 7 nodes — sindhu, gaṅgā, paruṣṇī,
sarayu, śutudrī, vipāś, yamunā — and no Sarasvatī.

### 1.3 `vajra` and `āyudha` are not typed `Weapon` — **VERIFIED**

```
VG:CONCEPT:AYUDHA-WEAPON      labels ["Concept","DomainEntity","Object"]  node_type OBJECT
VG:CONCEPT:VAJRA-THUNDERBOLT  labels ["Concept","DomainEntity","Object"]  node_type OBJECT
MATCH (n:Weapon) -> 3 nodes: jyā (bowstring), pāśa (noose), svadhiti (axe)
```

So `MATCH (:Weapon)` answers "which weapons occur in the corpus" with a bowstring, a
noose and an axe, while the bow, the arrow, the shaft, Indra's bolt and the word *āyudha*
itself are all invisible to it. `VAJRA-THUNDERBOLT` compounds the error: its `broader`
already points at `AYUDHA-WEAPON`, so before the fix the taxonomy asserted that a
Weapon-family entity's parent is a plain Object.

**Fix.** Both re-typed `OBJECT → WEAPON` in the `retypings` block. `SUPERLABELS` maps
`Weapon → (Object,)`, verified in the dry run:

```
VG:CONCEPT:AYUDHA-WEAPON      WEAPON -> ('Weapon', 'Object')
VG:CONCEPT:VAJRA-THUNDERBOLT  WEAPON -> ('Weapon', 'Object')
```

so no existing question becomes harder to ask. Aliases probed and read, all kept:

| alias | token hits | reading |
|---|---|---|
| `āyudhā` `āyudhāni` `āyudham` | 24 | the gear a warrior or god is armed with |
| `iṣuḥ` `iṣum` `iṣavaḥ` | 44 | arrow |
| `dhanuḥ` `dhanur` `dhanvanā` `dhanvanaḥ` | 47 | bow |
| `śaravyā` | 5 | arrow-volley |
| `vajraḥ` `vajro` `vajram` `vajraṃ` `vajreṇa` `vajrī` `vajrin` `vajrasya` `vajrabāhuḥ` `vajrivaḥ` | 388 | the bolt |

The English alias `bow` was already dropped from `AYUDHA-WEAPON` by the base registry
(21% of its hits are the verb, "let the four directions bow to me"); that stays dropped.

### 1.4 The fifth defect, not in the brief: `amīvāḥ` matches its own negation

Found while probing the split. `amīvāḥ` folds to 6 characters, clears
`MIN_SANDHI_ALIAS_CHARS`, and on the sandhi path sits inside **`anamīvāḥ`, "free from
disease"** — the exact opposite sense — plus the boundary glue
`sanemyasmadyuyavannamīvāḥ`. 5 of its 15 sandhi hits are wrong, and **this alias is
already live on `VG:CONCEPT:YAKSMA-DISEASE`**, so it is a defect in the shipped registry
and not merely a risk in the new file. This is the `mṛtasya`-inside-`amṛtasya` failure
mode that `SANDHI_SUPPRESSED_ALIASES` exists for, and it slipped through because the
length floor cannot know about negation prefixes.

### 1.5 Sweep for further mis-typings of the same kind

`data/registry/concepts.yaml` (89), `domain_entities_material.yaml` (45) and
`domain_entities_concern.yaml` (29) were checked entity by entity for a type that blocks a
predicate the entity plainly wants. Findings:

| entity | typed | problem | verdict |
|---|---|---|---|
| `VG:CONCEPT:RAKSAS-DEMON` | `CONCEPT` | `PROTECTS_FROM` has range `{Condition, HumanConcern}`, so no protective edge to the demon can be emitted at all. This is the third mis-typing of the same class as `yakṣma`-as-`State`. | **RE-TYPED → `CONDITION`** |
| `VG:CONCEPT:SATRU-ENEMY` | `CONCEPT` | same blocked predicate, but its alias set mixes hostile-intent words (`śatru`, `amitra`, `arāti`) with ethnonyms (`dāsam`, `dāsīḥ`, `dasyum`, `dasyavaḥ`, `dāsasya`). Re-typing would make "this passage protects from the Dāsa" assertable of Rigvedic passages that *describe peoples*. | **REFUSED** — see §5 |
| `VG:CONCEPT:GARBHA-EMBRYO` | `STATE` | correct. An embryo is a state and takes no concern predicate; V1's `no_typed_edge` listing is right. | no change |
| `VG:CONCEPT:SVASTI-WELLBEING` | `STATE` | arguably a `HUMAN_CONCERN` — it is "the closing wish of a great many hymns" by its own definition. But its alias set includes `śivam`/`śivā` and `subhagā`, which are predicated of gods and of objects as often as wished for. **Deferred, recorded, not changed**: a retype here needs the alias set re-read first, which is a separate pass. | deferred |
| `VG:CONCEPT:BHESAJA-HEALING` | `CONCEPT` | correct as-is. It is the act of healing, not an affliction and not a wish-word; `TREATS` would need it to be a `Condition`, which it is not. | no change |
| `VG:CONCEPT:RAJAN-KINGSHIP` | `CONCEPT` | holds `rāṣṭram`, `rāṣṭraṃ`, `kṣatram`. Arguably a royal `HUMAN_CONCERN`, but the alias set is also every descriptive mention of a king in the Rigveda. **Deferred, recorded.** | deferred |
| `VG:CONCEPT:AHI-SERPENT` | `ANIMAL` | correct, and it already claims `sarpān`, which is why V3's named snakes are `pṛdāku`, `svaja` and `vṛścika` and not a second generic snake. | no change |
| `VG:CONCEPT:HIRANYA-GOLD` | `SUBSTANCE` | already fixed — `NODE_TYPE_OVERRIDES` re-types it `METAL`. Cited as the precedent the V3 re-types follow. | already fixed |

Two entities (`SVASTI-WELLBEING`, `RAJAN-KINGSHIP`) are recorded as deferred rather than
silently changed, because in both cases the retype is only safe after the alias set has
been read, and reading them was not in this pass.

---

## 2. Alias probe table — every candidate, every rejection

**Method.** `scripts/probe_domain_aliases.py` semantics: a token pass (the alias must
equal a whole word of the folded surface) and a sandhi pass (substring of the
boundary-free surface, for aliases of ≥ `MIN_SANDHI_ALIAS_CHARS` = 6), with host-token
and intrusion-share analysis. Candidate forms were discovered by enumerating every folded
token in the corpus beginning with a stem, so no form was invented; then each was read
with `scripts/show_passage.py`.

**Totals.** 165 Sanskrit aliases stand. **42 candidate forms were read and rejected**,
each with the passage that rejected it. **23 candidate words token-matched nothing
anywhere in the corpus** and are recorded as absent rather than rejected. 152 surviving
and borderline forms additionally went through the full two-pass host/intrusion probe,
which is what caught the five sandhi hazards in §2.4.

### 2.1 Accepted — conditions

| entity | aliases (token hits) | distribution | read at |
|---|---|---|---|
| `TAKMAN-FEVER` | `takman`(7) `takmane`(6) `takmann`(2) `takmanaḥ`(1) `takmanā`(1) `takmā`(5) `takmānaṃ`(9) `takmānam`(1) `takmanāśana`(1) `takmanāśanam`(1) | AV 33/33 | AVS 1.25.1–4, 4.9.8, 5.4.1/2/9, 5.22.1–14, 5.30.16, 6.20.1–3, 9.8.6, 11.2.22/26, 11.4.11, 12.5.31, 19.34.10, 19.39.1/10 — all 33 read |
| `YAKSMA-DISEASE` | 18 forms (92 occ, 88 mantras) | AV 73 RV 14 YV 5 | AVS 2.33.1–3, 3.31.1–3, 9.8.10–12, 14.2.10, 19.38.1; RV 10.97.11/13; VSM 12.85/12.87 |
| `AMIVA-AFFLICTION` | `amīvā`(9) `amīvāḥ`(10) `amīvāṃ`(1) `amīvāś`(1) `amīvahā`(4) `amīvacātanīḥ`(3) `amīvacātanaḥ`(1) `amīvacātanam`(1) `amīvacātanaṃ`(1) | AV 10 RV 18 YV 3 | AVS 7.42.1, 7.84.1, 8.7.14, 19.34.9; RV 1.18.2, 1.91.12, 7.55.1, 7.71.2, 2.33.2, 10.137.6 |
| `RAPAS-BODILY-HURT` | `rapaḥ`(11) `rapas`(2) `rapasā`(3) `rapaso`(2) | AV 4 RV 12 YV 2 | AVS 4.13.2/3, 5.4.10; RV 7.50.1–3, 2.33.3/7, 7.34.13, 8.18.16 |
| `APACIT-SWELLINGS` | `apacitām`(3) `apacitaḥ`(2) `apacit`(1) `apacitāṃ`(1) `apacito`(1) | AV 8 occ / 7 mantras | AVS 6.25.1–3, 6.83.1/3, 7.74.1, 7.76.2 |
| `JAYANYA-DISEASE` | `jāyānya`(1) `jāyānyam`(1) `jāyānyaḥ`(1) `jāyānyo`(1) | AV 5 occ / 4 mantras | AVS 7.76.3/4/5, 19.44.2 |
| `KILASA-LEUCODERMA` | `kilāsaṃ`(3) `kilāsasya`(1) `kilāsabheṣajam`(1) `kilāsanāśanam`(1) | AV 6 occ / 4 mantras | AVS 1.23.1/2/4, 1.24.2 |
| `PALITA-GREYING` | `palitaṃ`(2) | AV 2/2 | AVS 1.23.1/2 |
| `VIDRADHA-ABSCESS` | `vidradhasya`(2) `vidradhaṃ`(1) | AV 3/3 | AVS 6.127.1/3, 9.8.20 |
| `SIRSAKTI-HEADACHE` | `śīrṣaktim`(2) `śīrṣaktiṃ`(1) `śīrṣaktir`(1) `śīrṣāmayam`(1) `śīrṣāmayaṃ`(1) | AV 6 occ / 5 mantras | AVS 5.4.10, 9.8.1, 12.2.19/20, 12.5.23 |
| `KARNASULA-EARACHE` | `karṇaśūlaṃ`(2) | AV 2/2 | AVS 9.8.1/2 |
| `ANGABHEDA-LIMB-SPLITTING` | `aṅgabhedo`(1) `aṅgabhedam`(1) | AV 2/2 | AVS 5.30.9, 9.8.5 |
| `VISALPAKA-AILMENT` | `visalpakam`(2) `visalpakaḥ`(1) `visalpakaṃ`(1) `visalpasya`(1) | AV 5 occ / 4 mantras | AVS 6.127.3, 9.8.2/5/20 |
| `HRDDYOTA-HEART-BURN` | `hṛddyoto`(1) `hṛddyotabheṣajam`(1) | AV 2/2 | AVS 1.22.1, 6.24.1 |
| `VATIKRTA-WIND-AILMENT` | `vātīkṛtasya`(1) `vātīkṛtanāśanī`(1) | AV 2/2 | AVS 6.44.3, 6.109.3 |
| `KSIPTA-BRUISE` | `kṣiptabheṣajy`(1) `kṣiptasya`(1) | AV 2/2 | AVS 6.109.1/3 |
| `UNMADA-MADNESS` | `unmaditam`(1) `unmattam`(1) | AV 2 occ / 1 mantra | AVS 6.111.3 (both, in one verse) |
| `SEDI-DEBILITY` | `sedir`(3) `sedim`(1) `sediṃ`(1) | AV 5/5 | AVS 2.14.3, 4.11.10, 8.8.9/18, 12.5.24 |
| `ARAYA-MALIGNANT-SPRITE` | `arāyyaḥ`(6) `arāyān`(5) `arāyam`(1) `arāyebhyo`(1) `arāyakṣayaṇam`(1) `arāyacātanaṃ`(1) | AV 15 occ / 14 mantras | AVS 1.28.4, 2.14.3, 2.18.3, 2.25.3, 8.2.20, 8.6.4/5 |
| `DURHARD-MALEVOLENT` | `durhārdo`(18) `durhārdaḥ`(6) `durhārdaś`(1) `durhārdam`(1) | AV 26/26 | AVS 2.7.5, 4.9.6, 8.3.25, 10.6.1, 14.2.29, 19.28.2 |
| `SAPATHA-IMPRECATION` | `śapatho`(5) `śapathaś`(2) `śapathaḥ`(2) `śapathyād`(4) | AV 12 RV 1 (13 occ / 12 mantras) | AVS 2.7.2/5, 4.18.7, 5.14.5, 6.96.2, 7.112.2, 10.1.5 |
| `ABHISASTI-CALUMNY` | `abhiśaster`(7) `abhiśastim`(3) `abhiśastiṃ`(2) `abhiśastyā`(1) `abhiśastipā`(5) | AV 8 RV 9 YV 1 | AVS 3.1.1, 3.2.1, 6.120.2, 7.53.1, 2.13.3; RV 1.71.10, 3.30.1; VSM 34.18 |
| `ABHICARA-SORCEROUS-ATTACK` | `abhicāriṇaḥ`(1) `abhicārād`(1) | AV 2/2 | AVS 10.1.9, 10.3.7 |

### 2.2 Accepted — animals, plants, substances, objects

| entity | aliases (token hits) | distribution | read at |
|---|---|---|---|
| `PRDAKU-ADDER` | `pṛdākavaḥ`(4) `pṛdākūr`(2) `pṛdākvas`(1) `pṛdākū`(1) `pṛdākau`(1) `pṛdākoḥ`(1) | AV 10/10 | AVS 1.27.1, 3.27.3, 5.18.3/15, 6.38.1, 7.56.1, 10.4.11/13 |
| `SVAJA-CONSTRICTOR` | `svajasya`(2) `svajaṃ`(1) | AV 3/3 | AVS 10.4.10/15/17 |
| `VRSCIKA-SCORPION` | `vṛścikam`(1) `vṛścikasya`(1) `vṛścikas`(1) `vṛścika`(1) | AV 3 RV 1 | AVS 10.4.9/15, 12.1.46; RV 1.191.16 |
| `PIPPALI-PLANT` | `pippalī`(1) `pippalyaḥ`(1) | AV 2/2 | AVS 6.109.1/2 |
| `PRSNIPARNI-PLANT` | `pṛśniparṇy`(3) `pṛśniparṇi`(1) | AV 4/4 | AVS 2.25.1/2/3/4 |
| `AJASRNGI-PLANT` | `ajaśṛṅgy`(2) | AV 2/2 | AVS 4.37.2/6 |
| `LAKSA-PLANT` | `silācī`(2) `lākṣe`(1) | AV 3/3 | AVS 5.5.1/7/8 |
| `MADUGHA-PLANT` | `madughān`(1) `madughasya`(1) | AV 2/2 | AVS 1.34.4, 6.102.3 |
| `VISANAKA-PLANT` | `viṣāṇakā`(1) | AV 1/1 | AVS 6.44.3 |
| `BHANGA-HEMP` | `bhaṅgo`(1) | AV 1/1 | AVS 11.6.15 |
| `ASVATTHA-TREE` | `aśvattha`(5) `aśvattho`(4) `aśvatthāt`(1) `aśvattham`(1) `aśvatthe`(3) | AV 10 RV 2 YV 2 | AVS 3.6.2/5, 5.4.3, 5.5.5, 6.95.1; RV 1.135.8, 10.97.5; VSM 12.79 |
| `KHADIRA-TREE` | `khadirād`(2) `khadiram`(2) `khadirasya`(1) `khadirājiram`(1) | AV 5 RV 1 | AVS 3.6.1, 5.5.5, 8.8.3, 10.6.9/10; RV 3.53.19 |
| `ANJANA-OINTMENT` | `āñjana`(7) `āñjanaṃ`(4) `āñjanam`(1) `āñjanena`(3) `āñjanasya`(2) `traikakudam`(1) `traikakudaṃ`(1) `traikakuda`(1) | AV 19 RV 1 | AVS 4.9.3/5/8/9/10, 6.102.3, 12.2.31, 18.3.57, 19.44.2/3/6; RV 10.18.7 |
| `AUDUMBARA-AMULET` | `audumbaro`(3) `audumbareṇa`(1) `audumbarasya`(1) `audumbaraṃ`(1) `audumbaraḥ`(1) | AV 7/7 | AVS 19.31.1/2/3/4/6/13 |

### 2.3 Accepted — concerns, rite, river

| entity | aliases (token hits) | distribution | read at |
|---|---|---|---|
| `PARIPANA-DEFENCE` | `paripāṇaṃ`(4) `paripāṇam`(3) `paripāṇaḥ`(3) `paripāṇāya`(1) `paripāṇād`(1) `paripāṇo`(1) | AV 14 occ / 11 mantras | AVS 2.17.7, 4.9.2/3, 4.20.8, 8.5.1/16, 19.34.7, 19.35.3 |
| `DIRGHAYUTVA-LONG-LIFE` | `dīrghāyutvāya`(15) `dīrghāyur`(4) `dīrghāyutvam`(1) | AV 16 RV 4 | AVS 1.22.2, 1.35.1, 14.2.2/63; RV 4.15.9, 10.62.2, 10.85.39 |
| `VARCAS-SPLENDOUR` | `varcasā`(62) `varcase`(14) | AV 54 RV 7 SV 1 YV 23 occ (76 mantras) | AVS 1.35.1, 2.28.5, 3.5.1, 3.13.5 |
| `SABHA-ASSEMBLY` | `sabhā`(3) `sabhāyāṃ`(2) `sabhāsadaḥ`(2) `sabhāsu`(2) `samitiḥ`(4) `samitiś`(3) | AV 14 RV 2 (16 occ / 14 mantras) | AVS 3.29.1, 4.21.6, 5.19.15, 5.31.6, 6.64.2, 7.12.1, 8.10.5, 12.1.56, 15.9.2; RV 6.28.6, 10.191.3 |
| `SARASVATI-RIVER` | `sarasvatyām`(1) `sarasvatyāṃ`(1) | AV 1 RV 1 | AVS 6.30.1, RV 3.23.4 |

### 2.4 Rejected — read, and the passage that rejected it

| rejected alias | hits | the passage that rejected it | why |
|---|---|---|---|
| `palitasya` | 2 | RV 1.164.1 "this benignant Priest, with eld grey-coloured"; AVS 9.9.1 "this pleasant hoary invoker" | *palitá* of a man, not the ailment AVS 1.23 removes |
| `kilāsatha` | 1 | RV 10.97.5 "The Holy Fig tree is your home" | not the disease under any reading |
| `kilāsamahne` | 1 | VSM 30.21 "for the Moon a leper" | the reading is right but the token is the glue `kilāsam`+`ahne`; unusable as an alias |
| `apacitiṃ` | 1 | RV 4.28.4 "took great vengeance with your murdering weapons" | *apaciti* 'requital', a different word |
| `vidradhe` | 1 | RV 4.32.23 "upon a new-wrought post" | not the abscess |
| `rapad` | 3 | AVS 18.1.19 "Prateth the Gandharvī"; RV 5.61.9; RV 10.11.2 | root *rap-* 'to prate' |
| `rapati` | 1 | RV 10.61.18 "thus speaks in kindness" | same root |
| `rapat` | 1 | RV 1.174.7 "the bard sang forth in inspiration" | same root |
| `rapa` | 1 | VSM 7.37 | no affliction reading in the stored translation |
| `sedima` | 2 | RV 5.8.4; RV 8.49.6 | perfect of *sad-*, a verb |
| `sedimā` | 1 | RV 1.89.2 | same |
| `svaja` | 1 | AVS 5.14.10 | imperative of *svaj-* 'to embrace' |
| `svajasva` | 1 | AVS 12.3.12 | same |
| `svajanmanā` | 1 | RV 7.1.12 | *sva-janman* 'own birth' |
| `taimātasya` | 2 | AVS 5.13.6 "the Timātan (?) black serpent" | Whitney's own query mark; no entity authored |
| `pippalaṃ` | 4 | AVS 9.9.20, RV 1.164.20 "the one eats the sweet berry" | *pippalá*, the berry of the two-eagles riddle, not the medicinal *pippalī* |
| `pippalam` | 1 | RV 5.54.12 | same |
| `aruṣ-` family (22 forms) | 90 | RV 3.15.3, RV 4.58.7, RV 1.6.1 — *aruṣá* 'ruddy', Agni's horses | the wound word is a homonym trap; no wound entity authored |
| `khadiro` | 1 | AVS 20.131.14 — **no stored translation** | could not be read, so not written down, even though the entity is sound |
| `sabhāṃ` | 2 | AVS 19.55.5, whose stored translation is about food and shows no assembly reading | rejected; the other five `sabhā-` aliases carry the entity |
| `varcasa` | 9 | hosts `brāhmaṇavarcasam`×5, `hastivarcasaṃ`, `hatavarcasaḥ` | 64% intrusion; other people's splendour, and once its loss |
| `varcas` | 4 | same intrusion set, over 136 sandhi hits | bare stem unusable |
| `rāṣṭraṃ` `rāṣṭram` `rāṣṭre` | 55 | — | claimed by `VG:CONCEPT:RAJAN-KINGSHIP`; see §5 |
| `sarasvatī` | 103 | AVS 5.23.1 "worked in is divine Sarasvatī" | goddess |
| `sarasvatīm` | 8 | AVS 5.7.4 "Sarasvatī, Anumati, Bhaga, we going call on" | goddess |
| `sarasvatīṃ` | 12 | AVS 3.20.7 "Vāta, Vishṇu, Sarasvatī, and the vigorous Savitar" | goddess |
| `sarasvati` | 25 | AVS 4.4.6 "now, goddess Sarasvatī!" | goddess |
| `sarasvaty` | 5 | RV 6.61.5 "Whoso, divine Sarasvati, invokes thee" (4 of its 5 hits) | goddess |
| `sarasvatyā` | 17 | AVS 5.7.5 "with speech, with Sarasvatī, mind-yoked" | goddess |
| `sarasvatyai` | 22 | AVS 14.2.20 "pay homage to Sarasvatī and to the Fathers" | goddess |
| `sarasvataḥ` | 1 | RV 7.96.6 "Sarasvan's breast" | masculine Sarasvān, a different figure |
| `sarasvatīvator` | 1 | RV 8.38.10 "Sarasvati's associates" | goddess |
| `sarasvatīḥ` | 1 | AVS 5.12.8 "let the three goddesses ... sit upon this barhís" | goddesses |
| `sarasvatir` | 1 | AVS 6.100.1 "the three Sarasvatīs have given" | goddesses |
| `vilohita-` (5 forms) | 5 | VSM 16.7 / 16.52 / 16.58 — a colour, in the Rudra litany | AVS 9.8.1's "anæmia (? vilohitá)" is outnumbered by its own paradigm |
| `asthisraṃsaṃ` | 1 | AVS 6.14.1 "the bone-dissolving ... balā́sa" | an epithet of *balāsa*, which is an existing entity; no new node |
| `asthijasya` | 1 | AVS 1.23.4 "the bone-born leprous spot" | an epithet of *kilāsa*; no new node |
| `udyugam` | 1 | AVS 5.22.11 "the udyugá (?)" | Whitney does not identify it, and this pass does not invent an identification |
| `viṣūcī-` family | 29 | RV 1.164.31, AVS 1.19.1 — 'in all directions' | not a disease |
| `bhaṅgurāvataḥ` and 5 more `bhaṅg-` forms | 15 | RV 7.104.7, AVS 8.3.22 — 'deceitful' / 'break' | `BHANGA-HEMP` keeps `bhaṅgo` only |
| `arusrāṇam` | 2 | AVS 2.3.3 / 2.3.5 | genuine, but 2 hits of a compound is too little to name an affliction on |
| `piśāca-`, `yātudhāna-` forms | 114 | — | already claimed by `VG:CONCEPT:RAKSAS-DEMON`; authoring a sibling would repeat the takman fold |

### 2.5 Absent — token-matched nothing anywhere in the corpus

`alajī`, `alaji`, `glāu`, `viśalya`, `śatāvarī`, `tālī`, `kaṇṭakā`, `prapharvi`,
`puṃsav-`, `sūtī`, `janayitr-`, `sammanas`, `sāmanas`, `priyaṃkar-`, `manaskām-`,
`śokaja`, `abhiṣec-`, `aligī`, `karait`, `aruḥ`, `pāman`, `pāmnā`, `pāpman` — 23 words.
Recorded as absent, not rejected: the corpus does not name them, so nothing was authored,
and nothing was guessed at.

The one worth calling out: **`pāmán`, the scab, is in the translation and not in the
text.** Whitney renders AVS 5.22.12 "O fever, together with thy brother the *balā́sa* and
thy sister the cough, together with thy cousin the scab (*pāmán*)", but the stored
Sanskrit surface of that mantra reads `pāpmā́` — *pāpman*, 'evil':

```
tákman bhrā́trā balā́sena svásrā kā́sikayā sahá |
pāpmā́ bhrā́tṛvyeṇa sahá gáchāmúm áraṇaṃ jánam ||12||
```

An entity built on Whitney's gloss would have been an entity built on a word the corpus
does not have there.

### 2.6 Sandhi hazards — the five aliases that need a companion suppression

Kept, because they are correct on the token path, but they will emit false positives on
the sandhi path until they are added to `SANDHI_SUPPRESSED_ALIASES` in
`src/vedagraph/enrich/concepts.py` — an edit this pass is forbidden to make and therefore
reports as a **blocker**.

| alias | intrusion | host it sits inside | consequence if unsuppressed |
|---|---|---|---|
| `amīvāḥ` | 33% | `anamīvāḥ` "free from disease", `sanemyasmadyuyavannamīvāḥ` | affliction asserted of passages that deny it. **Already live** on `YAKSMA-DISEASE`. |
| `rapaso` | 33% | `nārīrapaso` = glue of *nā́rīr apáso* | 1 false passage |
| `apacit` | 10% | `apacitiṃ` (RV 4.28.4), `dadhadindriyamūrjamapacitiṃṃ` | *apaciti* 'requital' read as a swelling |
| `arāyam` | — | 7 of 8 sandhi hits are word-boundary glue | 7 false passages |
| `sarasvatyām` | — | `sarasvatyā manoyujā` (AVS 5.7.5), `sarasvatyā meṣasya` (VSM 21.46, 21.47) | **3 goddess passages typed `River`** — the whole basis of the new node |

Six aliases fall *below* the 6-character floor and are safe on the token path only, which
is the floor doing its job: `takmā`(5), `rapaḥ`(5), `rapas`(5), `sedir`(5), `sedim`(5),
`sabhā`(5), `lākṣe`(5). Left unsuppressed as harmless: `audumbaro`/`audumbaraḥ` (hosts
`maudumbaro`, `caudumbaro`, `sarvaudumbaraḥ` are all boundary glue of the same word),
`sabhāyāṃ` (`yatsabhāyāṃ`), `āñjana` (`devāñjana`), `aśvattha`, `rāṣṭram`, `varcasā`,
`varcase`, `abhiśastipā` — all read, all the same word.

### 2.7 Interaction with the concurrent vocative pass

While this pass was running, `data/registry/concepts.yaml` acquired a V3 refinement that
strips **vocatives** from appellative entities, on the principle that "you cannot address
a thing that is not a being", so `agne`, `soma`, `sūrya` and `pṛthivi` belong to the
deity and not to the element. Checked against this file, because it bears on two aliases:

- **`takman` and `takmann` are vocatives** — AVS 1.25.1 "then do thou, O fever, complaisant,
  avoid us"; AVS 5.22.2 "now then, O fever". Under the new principle a vocative belongs to
  the deity **when there is a deity of that name**, and there is not: `data/registry/devatas.yaml`
  (214 entries) contains no `VG:DEVATA:TAKMAN`, and the Anukramaṇī's ascription is
  *takmanāśana*, "fever-**destruction**" — the destruction, not the fever. The
  Atharvaveda personifies the affliction it is dismissing; the addressee is the affliction.
  So the vocative stays with the `Condition`, and the two principles do not collide.
- **The convergence is worth noting for §3.** The vocative pass says the *vocative* of
  Sarasvatī is the goddess. `sarasvati`, the short-`i` form, is exactly that vocative
  (AVS 4.4.6 "now, goddess Sarasvatī!"), and it is rejected in §2.4. The `River` node
  rests on the *locative*. Two different cases, two different referents, and the corpus's
  own morphology drawing the line in both directions.
- **One adjacent case flagged, not fixed:** `kuṣṭha` is a bare vocative at AVS 5.4.6 and
  19.39.2 ("come, O *kúṣṭha*"), and it is a live alias of `VG:CONCEPT:KUSTHA-PLANT`. There
  is no `VG:DEVATA:KUSTHA` either, so by the reasoning above it is safe — but the AV
  ascription on AVS 19.39 is *kuṣṭhadevatyam*, so if the ascription layer ever becomes
  `Devata` nodes this is the next alias to re-check. Not this pass's file to change.

Re-verified after that change landed: the merge dry run still reports **204 entities, 0
alias collisions**, and none of the four re-typed or replaced entities was touched by it.

---

## 3. The Sarasvatī `River` decision: **yes**, on the locative singular alone

**The prior decision, and what was right about it.** `domain_entities_material.yaml`
records under "What is deliberately NOT here": *"There is no SARASVATI-RIVER node. Its
forms token-match 172 mantras (RV 41, SV 3, YV 44, AV 15) and the great majority are the
goddess ... A RIVER node claiming them would assert 'this passage is about a river' of
well over a hundred passages that are about a deity."* That reasoning is sound and this
report does not overturn it. What it overturns is the assumption that a `River` node would
have to be built on those forms.

**Re-measured.** Enumerating all 37 folded tokens beginning `sarasvat-`: **206 mantras,
RV 69, SV 3, YV 99, AV 35** (the earlier 172 was on a narrower form set). Of these, 8 have
no stored translation. The corpus-wide river share is small and the Rigvedic share is much
larger — RV 6.61, 7.95, 7.96 are river hymns end to end, and RV 7.36.6 "Mother of Floods,
the seventh", RV 2.41.16 "best of Rivers", RV 10.64.9 "Sindhu, Sarasvati, and Sarayu with
waves" are unambiguous. But the split is **not recoverable from any of those forms**: the
same `sarasvatī` that is a river at RV 7.95.1 is a goddess at AVS 5.23.1.

**One form is different, and the difference is grammatical, not statistical.**

| alias | token hits | reading | witness |
|---|---|---|---|
| `sarasvatyām` | 1 | **river** | AVS 6.30.1 — "This barley, combined with honey, the gods plowed much **on the Sarasvatī**, in behalf of Manu" |
| `sarasvatyāṃ` | 1 | **river** | RV 3.23.4 — "**On** man, on Apaya, Agni! **on the rivers** Drsadvati, Sarasvati, shine richly" |

**2 of 2, corpus-wide.** The locative singular of a river name means *on it*, and a
goddess is not something one ploughs on or shines on. That is a reason, not a frequency.
Note that AVS 6.30.1 is one of the passages my keyword classifier put in the
*deity* bucket, because Whitney's English contains no river word at all — the preposition
"on" is the only signal, and the case ending is what carries it. A statistical pass over
translations would have missed this and did.

**Is two hits enough?** It is exactly the standard the existing river set meets. Measured
token hits, all six:

| entity | aliases and token hits |
|---|---|
| `GANGA-RIVER` | `gaṅge` 1 |
| `YAMUNA-RIVER` | `yamunā` 1, `yamune` 1 |
| `SARAYU-RIVER` | `sarayuḥ` 2 |
| `PARUSNI-RIVER` | `paruṣṇī` 1, **`paruṣṇyām` 1** |
| `VIPAS-RIVER` | `vipāṭ` 1, `vipāśam` 1 |
| `SUTUDRI-RIVER` | `śutudri` 1 |

`PARUSNI-RIVER` already uses precisely this device: its second alias is the locative
`paruṣṇyām`. So `SARASVATI-RIVER` on 2 locative hits is neither the weakest node in the
set nor a new kind of evidence in it — it is the same device the file already trusted.

**Decision: author `VG:CONCEPT:SARASVATI-RIVER`, `node_type: RIVER`, on
`sarasvatyām` + `sarasvatyāṃ` and nothing else.** `broader: [VG:CONCEPT:SINDHU-RIVER]`,
`related_devatas: [VG:DEVATA:SARASVATI, VG:DEVATA:NADYAH]` so a reader can traverse from
the river to the goddess and see that the corpus treats them as one being. The dry run
confirms the labels: `RIVER -> ('River', 'Place')`.

**What the node deliberately does not claim.** RV 6.61, 7.95 and 7.96. Those hymns praise
a being who is a river *and* a goddess, their case forms do not distinguish the readings,
and they are already reachable through `VG:DEVATA:SARASVATI`'s `HAS_DEVATA` edges. A
researcher asking "where is the Sarasvatī river named" gets two passages where the grammar
settles it; a researcher asking "what does the corpus say about Sarasvatī" gets all 206
through the deity. Those are different questions and they should not return the same
answer.

**What would change the answer back.** One thing: the sandhi suppression in §2.6. Without
it, `sarasvatyām` matches three more passages by word-boundary glue — AVS 5.7.5
"with speech, with Sarasvatī, mind-yoked" and VSM 21.46/21.47 "of Sarasvatî, of the ram
the sacrifice" — all three of which are the goddess. That would make the node 2 of 5
correct, i.e. 40% precision, and at 40% it should not be created. **The `River` node is
justified only with the suppression applied.** If the architect declines the suppression,
decline the node.

---

## 4. Fever, worked end to end

The target was that "what does the Atharvaveda say about fever?" returns a connected
evidence graph. Here is what it returns, simulated against the V3 registry with the
suppressions applied.

### 4.1 The condition

`VG:CONCEPT:TAKMAN-FEVER`, `Condition`, matches **33 passages, 33 of 33 Atharvaveda**.
Before: no fever entity existed; 15 of those 33 arrived at a `State` node called
"disease (yakṣma)", 8 arrived nowhere, and none carried an affliction edge.

The 33 passages, by hymn: **AVS 5.22** (13 — the fever hymn), **1.25** (4), **5.4** (3),
**6.20** (3), **11.2** (2), **19.39** (2), and one each in 4.9, 5.30, 9.8, 11.4, 12.5,
19.34.

### 4.2 Typed edges on those 33 passages

| predicate | edges | to |
|---|---|---|
| `TREATS` (TIER_D) | **33** | `TAKMAN-FEVER` |
| `TREATS` | 4 | `BALASA-DISEASE` |
| `TREATS` | 3 | `KASA-COUGH` |
| `PROTECTS_FROM` (TIER_D) | 2 | `YAKSMA-DISEASE` |
| `PROTECTS_FROM` | 1 | `VISA-POISON` |
| `PROTECTS_FROM` | 1 | `RAKSAS-DEMON` (via the re-type) |

The co-affliction edges are not noise; they are the corpus's own nosology. AVS 5.22.12:
*"O fever, together with thy brother the balā́sa [and] thy sister the cough ... go to yon
foreign people."* The graph now says balāsa, kāsa and takman are co-treated in the same
verses, because that verse says they are family.

### 4.3 Plain mentions on those 33 passages — 26 distinct entities

| type | entities (passages) |
|---|---|
| `Condition` | `BALASA-DISEASE` (4), `KASA-COUGH` (3), `YAKSMA-DISEASE` (2), `VISA-POISON` (1), `RAKSAS-DEMON` (1) |
| `Plant` | **`KUSTHA-PLANT` (2)**, **`JANGIDA-PLANT` (1)** |
| `Substance` | **`ANJANA-OINTMENT` (1)**, `SOMA-DRINK` (1) |
| `Action` | `NAMAS-HOMAGE` (4), `JANMAN-BIRTH` (1) |
| `NaturalPhenomenon` | `AGNI-FIRE` (3), `AP-WATERS` (1), `VIDYUT-LIGHTNING` (1) |
| `Place` | `KSETRA-FIELD` (2), `PARVATA-MOUNTAIN` (1) |
| `Object` | `BARHIS-SACRED-GRASS`, `SAMIDH-FUEL`, `ASMAN-PRESSING-STONE` (1 each) |
| `Weapon` | **`VAJRA-THUNDERBOLT` (1)** — reachable as a Weapon only via the §1.3 re-type |
| `Animal` | `AHI-SERPENT` (1) |
| `CosmicEntity` | `DYAUS-HEAVEN`, `PRTHIVI-EARTH` (1 each) |
| `Concept` | `JANA-PEOPLE` (2), `PRANA-BREATH`, `MRTYU-DEATH`, `RAJAN-KINGSHIP` (1 each) |

The three that matter, with the line that puts them there:

- **`kuṣṭha`** — AVS 5.4.1: *"Thou that wast born on the mountains, strongest of plants,
  come, O kúṣṭha, effacer of takmán, effacing the fever from here."* The remedy compound
  `takmanāśana` is in that same verse, which is why `TAKMAN-FEVER` is in `treats` on
  test (1) and not on a bare name match.
- **`jaṅgiḍá`** — AVS 19.34.10: *"The crusher, the burster, the balā́sa, the side-ache,
  the takmán of every autumn, may the jaṅgiḍá make sapless."*
- **`āñjana`** — AVS 4.9.8: *"Three are the slaves of the ointment — fever (takmán),
  balā́sa, then snake: the highest of mountains, three-peaked by name, is thy father."*
  All three of that verse's slaves are now separate entities that this one passage
  matches: `TAKMAN-FEVER`, `BALASA-DISEASE`, `AHI-SERPENT`.

### 4.4 The 12 fever hymns as a whole — 229 verses

Verse-level matching is narrow by design. Expanding to the sūkta through `CONTAINS`:

**Plants, substances and objects across the 12 hymns:** `KUSTHA-PLANT` (14 verses),
`ANJANA-OINTMENT` (8), `OSADHI-PLANTS` (7), `JANGIDA-PLANT` (6), `HIRANYA-GOLD` (3),
`ASVATTHA-TREE` (2), and one verse each of `ASMAN-PRESSING-STONE`, `BARHIS-SACRED-GRASS`,
`SAMIDH-FUEL`, `SOMA-DRINK`, `YAVA-BARLEY`, `RATHA-CHARIOT`.

**Afflictions across the 12 hymns — 20 distinct `Condition` nodes:** `TAKMAN-FEVER` (33),
`YAKSMA-DISEASE` (14), `BALASA-DISEASE` (6), `VISA-POISON` (6), `KRTYA-SORCERY` (5),
`SIRSAKTI-HEADACHE` (3), `KASA-COUGH` (3), `VISALPAKA-AILMENT` (3),
`VISKANDHA-AFFLICTION` (2), `DUSVAPNYA-BAD-DREAM` (2), `RAKSAS-DEMON` (2),
`ANGABHEDA-LIMB-SPLITTING` (2), `KARNASULA-EARACHE` (2), and one each of
`SAPATHA-IMPRECATION`, `DURHARD-MALEVOLENT`, `RAPAS-BODILY-HURT`, `HARIMAN-JAUNDICE`,
`VIDRADHA-ABSCESS`, `SEDI-DEBILITY`, `AMIVA-AFFLICTION`. **Eight of those twenty are new
in V3**, and one — `TAKMAN-FEVER` — is the one the question was about.

**Human concern:** `PARIPANA-DEFENCE` on 3 verses. **This is the weakest link and it is
reported as weak.** At verse level, `ADDRESSES_CONCERN` on the 33 fever passages is
**zero**: none of the seven `HUMAN_CONCERN` alias sets occurs in a fever verse. The fever
graph reaches the human concern only at hymn scope, and only through defence. What the
Atharvaveda wants when it treats a fever is stated in the *act* — homage paid, the fever
sent to the Mūjavants — not in a wish-noun the matcher can find.

### 4.5 Cross-Veda reuse: none, and that is the finding

```cypher
MATCH (p:Passage)-[r:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM|VARIANT_OF]-(o:Passage)
WHERE p.canonical_key IN <the 229 verses of the 12 fever hymns>
RETURN type(r), o.veda, count(*)
```
returns **0 rows**.

That is a real signal and not missing data: the same query over the whole Atharvaveda
returns **2,002 edges** (`NEAR_PARALLEL_OF` RV 752, `EXACT_PARALLEL_OF` RV 551,
`NEAR_PARALLEL_OF` SV 326, `NEAR_PARALLEL_OF` YV 162, `VARIANT_OF` SV 132 / YV 41 / RV 22,
`EXACT_PARALLEL_OF` SV 9 / YV 7). So the Atharvaveda's fever material is shared with no
other Veda at either the word level (0 `takman-` tokens outside AV) or the verse level
(0 reuse edges). **Fever is Atharvavedic property.** A researcher can now read that off
the graph instead of assuming it.

### 4.6 One measured limitation

`MAX_CONCEPTS_PER_PASSAGE` is 4. Two of the 33 fever verses — **AVS 5.22.1** (Agni, Soma,
the pressing-stone, Varuṇa, the hearth, the barhís, the fuel) and **AVS 6.20.2** (Rudra,
fever, Varuṇa, sky, earth, herbs) — carry more than four matches, so their weakest
mentions will be dropped. The drop is counted and reported by the enrichment run and is
not silent, but it means the two densest fever verses are the two whose evidence is most
truncated. Worth a look before the cap is treated as settled.

### 4.7 What "connected" turned out to mean, and a blocker

The brief asked for `USES_PLANT` / `USES_SUBSTANCE` and `INVOKES_DEVATA` alongside the
concern predicates. Measured against `RELATIONSHIP_SIGNATURES`:

| requested | status |
|---|---|
| `USES_PLANT` | **does not exist** as a relationship type |
| `USES_SUBSTANCE` | exists, signature `Ritual -> {Substance, Plant}`. Domain is not `Passage` and not `Condition`; there are 4 `Ritual` nodes in the graph |
| `USES_OBJECT` | exists, `Ritual -> Object`. Same restriction |
| `INVOKES_DEVATA` | exists, signature `Ritual -> Devata`. A `Passage` cannot be its subject — and separately **the Atharvaveda has 0 `HAS_DEVATA` edges**, so no AV charm reaches a deity by any route |

Endpoint violations fail the build, so none of the three was authored. There is also **no
relationship type anywhere in `RELATIONSHIP_SIGNATURES` with a `Condition` endpoint other
than `TREATS` and `PROTECTS_FROM`**, both of which take `Passage` as subject. So there is
no legal way today to say "kuṣṭha treats takman" as a one-hop edge.

That is a named blocker, and it should not be routed around. The passage *is* the shared
evidence, and joining a herb to an ailment because both are named in one charm is an
inference about which of two co-mentioned entities acts on the other. The V1 predicates
file refuses that inference explicitly and the refusal still holds. What §4.3 shows is
that the two-hop join

```cypher
MATCH (c:Condition {concept_id:'VG:CONCEPT:TAKMAN-FEVER'})<-[t:TREATS]-(p:Passage)
      -[:MENTIONS_ENTITY]->(e)
WHERE e:Plant OR e:Substance OR e:Object
RETURN e.display_label, collect(p.canonical_citation)
```

answers the question *with the evidence attached*, which the one-hop edge would have
discarded. If the architect wants the convenience edge anyway, the honest shape is a
reified assertion in the V3 `SemanticAssertion` layer, where the instrument role has
somewhere to live and the passage stays attached. Named here, not built here.

---

## 5. The `śatru` / `rakṣas` / `sapatna` directional edge

The evaluator's closest single miss: protection has no directional edge to enemy, demon or
rival. Answered three different ways, because the three words are not in the same
evidential position.

| word | verdict | basis |
|---|---|---|
| **`sapatna`** rival | **SUPPORTED, no change needed** | `VG:CONCEPT:SAPATNA-RIVAL-OVERCOMING` is already `HUMAN_CONCERN`, so it is already inside `PROTECTS_FROM`'s declared range `{Condition, HumanConcern}`. It was simply listed under `addresses_concern` only. The rival charms both name the wish and ask deliverance from the rival — AVS 8.5.1 "heroic, rival-slaying, true hero, a very propitious protection" — so both predicates are true and neither is stronger. Added to `protects_from` as the single `promotions` row. |
| **`rakṣas`** demon | **SUPPORTED, requires the re-type** | `VG:CONCEPT:RAKSAS-DEMON` is `CONCEPT`, which no concern predicate accepts. Re-typed `CONDITION` on the precedent already inside the V1 concern file, which types `DURNAMAN-ILL-NAMED-BEINGS` and `KRTYA-SORCERY` as `CONDITION` and states in its own header that "worms, poison, sorcery, evil dream and the ill-named beings are causes or agents rather than kinds of sickness". Its alias set was re-read: `rakṣasaḥ`, `rakṣaso`, `rakṣasā`, `rakṣasām`, `rakṣo`, `rakṣāṃsi`, `piśācān`, `piśācāḥ`, `yātudhānam`, `yātudhānaḥ`, `yātudhānyaḥ`, `yātudhānān` — uniformly hostile beings, no ethnonym. The demon hymns AVS 1.7, 1.8, 8.3 and RV 10.87 ask expressly to be guarded from them. |
| **`śatru`** enemy | **REFUSED, and the refusal is the point** | `VG:CONCEPT:SATRU-ENEMY` is `CONCEPT` and could be re-typed the same way, but its alias set mixes hostile-intent words (`śatrum`, `śatrūn`, `śatroḥ`, `amitram`, `amitrān`, `arātim`, `arātīḥ`) with **ethnonyms**: `dāsam`, `dāsasya`, `dāsīḥ`, `dasyum`, `dasyūn`, `dasyave`, `dasyavaḥ`. A `PROTECTS_FROM` edge would then assert "this passage protects from the Dāsa" of Rigvedic passages that *describe peoples* — RV 4.28.4 "the Dasyus, abject tribes of Dasas" is a battle narrative, not a charm. That is a claim about a people rather than about a text, and it is the same class of error as folding four afflictions into one node. |

**The human enemy is nevertheless now reachable, narrowly and honestly**, through the new
`VG:CONCEPT:DURHARD-MALEVOLENT` (`Condition`): *durhārd*, "evil-hearted", **26 of 26
token occurrences Atharvavedic**, no ethnonym anywhere in the paradigm, and every passage
it matches is a charm against a hostile person — AVS 19.28.2 "burn together like heat
against all the evil-hearted", AVS 4.9.6 "from the terrible eye of an enemy — therefrom
protect us, ointment", AVS 8.3.25 "gore, O Jātavedas, the attacking enemy", AVS 14.2.29
the evil-hearted women kept from a bride. So "this passage protects from the malevolent"
is true of every passage the edge would touch, which is exactly what `SATRU-ENEMY` cannot
promise.

Net: **two of the three closed, the third closed by proxy with the direct route refused
in writing.** New `PROTECTS_FROM` reach for hostile agency: `RAKSAS-DEMON`,
`SAPATNA-RIVAL-OVERCOMING`, `DURHARD-MALEVOLENT`, `ARAYA-MALIGNANT-SPRITE`,
`SAPATHA-IMPRECATION`, `ABHISASTI-CALUMNY`, `ABHICARA-SORCEROUS-ATTACK`, alongside the V1
`KRTYA-SORCERY` and `DURNAMAN-ILL-NAMED-BEINGS`.

---

## 6. Coverage against the brief

| area | delivered | gap recorded |
|---|---|---|
| conditions and disease | 22 new `Condition` entities; the 4-way `yakṣma` split | `nirṛti` deferred (Condition or Devatā is unsettled); no wound entity (`aruṣ-` is a homonym trap) |
| healing | `BHESAJA-HEALING` already exists; V3 adds the five printed remedy compounds that license `TREATS` | — |
| plants and herbs | 9 new `Plant` entities on top of V1's 6 | `pūtudru`, `nitatni`, `rohiṇī` measured and not authored (1–4 hits with mixed readings) |
| poison | `VISA-POISON` exists; V3 adds the three named biters | `taimāta` refused on Whitney's own query mark |
| snakes | `PRDAKU-ADDER`, `SVAJA-CONSTRICTOR`, `VRSCIKA-SCORPION` under `AHI-SERPENT` | — |
| protection | `PARIPANA-DEFENCE`; the §5 directional edges | — |
| enemies | `DURHARD-MALEVOLENT`, `ARAYA-MALIGNANT-SPRITE`, `RAKSAS-DEMON` re-typed | `SATRU-ENEMY` refused in writing |
| love | `MADUGHA-PLANT`, the honey-plant of the two love charms | `KAMA-DESIRE` already exists; no *vaśīkaraṇa* vocabulary in the corpus |
| marriage | `VIVAHA-MARRIAGE` exists; `DIRGHAYUTVA-LONG-LIFE` reaches AVS 14.2 | — |
| childbirth | `PRASUTI-CHILDBIRTH` and `GARBHA-EMBRYO` exist | `puṃsavana`, `sūtī`, `janayitrī` all absent from the corpus |
| household | `SALA-HOUSE-BUILDING` and `GRHA-HOUSE` exist; `AUDUMBARA-AMULET` is the household-prosperity amulet | — |
| prosperity | `PUSTI-THRIVING` exists; `AUDUMBARA-AMULET`, `VARCAS-SPLENDOUR` added | `bala` refused as a duplicate of `OJAS-MIGHT` |
| funerals | `PITRYANA-FUNERARY-RITE` exists; `ANJANA-OINTMENT` reaches AVS 18.3.57 and RV 10.18.7 | — |
| royal concerns | `SABHA-ASSEMBLY` (the occasion) | **dominion refused**: `rāṣṭraṃ`/`rāṣṭram` are already `RAJAN-KINGSHIP`'s, and a sibling on the unclaimed `rāṣṭre` would hold 13 of 55 hits under a near-synonymous label — the very fold this report undoes |
| oaths | `SAPATHA-IMPRECATION`, `ABHISASTI-CALUMNY` | — |
| charms | `KRTYA-SORCERY` exists; `ABHICARA-SORCEROUS-ATTACK` added; `PRSNIPARNI-PLANT`, `AJASRNGI-PLANT`, `APAMARGA-PLANT` are the counter-charm herbs | — |

**New entities by type:** `CONDITION` 22 (+1 replaced), `PLANT` 9, `ANIMAL` 3,
`HUMAN_CONCERN` 3, `SUBSTANCE` 1, `OBJECT` 1, `SOCIAL_RITE` 1, `RIVER` 1 = **41 new**.
Simulated against the corpus, **all 41 match at least one passage**; none is a dead node.

**Simulated predicate totals under V3** (V1 ∪ V3, before the per-passage cap):

| predicate | entities | passage edges | tier |
|---|---|---|---|
| `TREATS` | 21 | 161 | TIER_D |
| `PROTECTS_FROM` | 15 | 605 | TIER_D |
| `ADDRESSES_CONCERN` | 7 | 381 | TIER_B |
| `USED_FOR_RITE` | 5 | 120 | TIER_B |

---

## 7. What a researcher must not conclude from a `TREATS` edge

`TREATS` is TIER_D, `L4_INTERPRETIVE_CLAIM`, and it stays there. This report earned it on
better evidence than V1 had — a printed remedy compound, or a match set read to the end —
and none of that better evidence changes what the edge means. Four things it does not say.

**It does not say the passage is a prescription.** `(:Passage)-[:TREATS]->(:Condition)`
means: *this verse was read as being directed at this affliction.* The reading rests on
one of two things — a compound the corpus itself prints (`takmanāśana`, "effacer of
takman"), or a match set small enough that every member was read and found to sit inside a
charm. Neither is an observation that anything was administered to anybody. AVS 5.22.7
carries a `TREATS` edge to fever, and what it does is *"O fever, go to the Mūjavants, or
to the Balhikas, further off; seek the wanton Çūdra woman."* That is a `TREATS` edge whose
therapy is deportation.

**It does not say a co-mentioned plant is the remedy.** There is no edge from `kuṣṭha` to
`takman` in this model, on purpose and not for want of a relationship type. When AVS 5.4.1
matches both, the graph says both are named in that verse and stops. Occasionally the verse
goes further and says which acts on which — that is what `takmanāśana` is — but the
matcher cannot tell that verse from AVS 4.9.8, where fever and the snake are both named as
the *ointment's* slaves and neither treats the other. Reading the plant edge off the
co-mention would get one right and one wrong with no way to know which.

**It does not say a `TREATS` edge and a `PROTECTS_FROM` edge differ in truth.** They
differ in what was checked. `TREATS` required an explicit remedy compound or an exhaustive
read; `PROTECTS_FROM` is where everything that failed those tests went. So
`YAKSMA-DISEASE` sits under `PROTECTS_FROM` despite having the printed compound
`yakṣmanāśanīḥ`, because 88 occurrences across four Vedas were not read one by one — and
`TAKMAN-FEVER` sits under `TREATS` with 36 occurrences that were. The predicate records
the strength of the *audit*, not the strength of the charm.

**It does not say the graph knows what the disease was.** `takman` is filed as "fever"
because Whitney renders every one of its 36 occurrences that way, and the corpus itself
sorts it by period, season and colour. It is not filed as malaria, and `balāsa`,
`viṣkandha`, `visalpaka` and `jāyānya` are left untranslated precisely because the corpus
gives their sites and their remedies and not their nature. Where the translator hedged, the
hedge is preserved: `apacit` is "swellings", `arāya` carries Whitney's three incompatible
renderings in its own definition, and `taimāta` and `udyuga` got no entity at all because
he marked both with a question mark. A `TREATS` edge to `VISALPAKA-AILMENT` tells you the
Atharvaveda has a charm for something it calls *visalpaka*. It does not tell you what
*visalpaka* is, and no amount of graph traversal will.

The one thing the edge does say, and says reliably: **here is a verse, here is the reason
it was read this way, and here is the affliction the reading is about.** Follow it to the
passage and read the passage. That is what the evidence layer is for.
