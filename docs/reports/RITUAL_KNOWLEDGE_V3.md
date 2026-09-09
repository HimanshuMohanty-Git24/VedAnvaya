# Ritual and Procedural Knowledge, V3

An independent scorecard scored the graph's ritual dimension **1 out of 5**: four rites,
35 apparatus edges, `HAS_STEP` = 0, `DESCRIBED_IN` = 0, over a corpus containing the whole
Vājasaneyi Saṃhitā. Measured against the live store before this pass, that was exactly
right:

```
MATCH (r:Ritual) RETURN count(r)                              -> 4
MATCH (:Ritual)-[r]->() RETURN type(r), count(r)              -> USES_OBJECT 11,
                                                                 PERFORMED_BY 6,
                                                                 INVOKES_DEVATA 5,
                                                                 USES_SUBSTANCE 4,
                                                                 PERFORMED_FOR 4,
                                                                 USES_OFFERING 3,
                                                                 BROADER_THAN 2   (= 35)
MATCH ()-[r:HAS_STEP]->() RETURN count(r)                     -> 0
MATCH ()-[r:DESCRIBED_IN]->() RETURN count(r)                 -> 0
MATCH (n:RitualRole) RETURN count(n)                          -> 5
MATCH (n:Action) RETURN count(n)                              -> 5
```

This pass raises that to eight rites, ten priestly offices, twelve ritual acts, 79
structural edges, 71 `DESCRIBED_IN` edges and 3 `HAS_STEP` edges, and adds 503 new
`MENTIONS_ENTITY` edges from 21 new entities. It also names two things it could not do and
one corpus defect it found, because those are load-bearing.

**Deliverables**

| file | contents |
|---|---|
| `data/domain/vedagraph_domain_v2/domain_entities_ritual_v3.yaml` | 21 entities: 4 `RITUAL`, 5 `RITUAL_ROLE`, 7 `ACTION`, 3 `OBJECT`, 2 `SUBSTANCE`. 40 Sanskrit aliases. |
| `data/domain/vedagraph_domain_v2/rituals_v3.yaml` | 8 rites: 4 new, 4 augments of `rituals.yaml`. `rituals.yaml` is not edited. |
| this report | evidence, refusals, the probe table, three Yajurvedic rites end to end, the `HAS_STEP` decision, and what must not be concluded. |

Both YAML files were validated mechanically, not by eye:

- The merged registry (`concepts.yaml` + material + concern + ritual\_v3 = **184** entities,
  against `MAX_CONCEPT_NODES` 260) passes `load_concepts(allowed_node_types=ALL_NODE_TYPE_NAMES)`:
  no duplicated folded alias, no unresolvable `broader`, no unresolvable `related_devatas`.
- Every endpoint in `rituals_v3.yaml` was checked against `RELATIONSHIP_SIGNATURES` through
  `labels_for_node_type`, and all 88 passage references (71 `described_in` + 17 in the
  `has_step` lists, 73 distinct keys) were checked against `load_corpus`. Zero violations.
- Coverage was measured with the production matcher `assign_concepts`, not with the probe
  script, which matters — see *The sandhi pass runs on the Sāmaveda only* below.

---

## 1. Rites accepted

| rite | id | new/augment | conf. | evidence in one line |
|---|---|---|---|---|
| soma cup drawing | `VG:CONCEPT:GRAHA-SOMA-DRAWING` | new | HIGH | `upayāmagṛhīto 'si` in 51 passages, all Yajurvedic; the cup inventory at VS 18.19–20; the apparatus inventory at VS 18.21 |
| sautrāmaṇī | `VG:CONCEPT:SAUTRAMANI` | new | MEDIUM | named at VS 19.31 and AVS 3.3.2; materials in one verse at VS 21.30–31; deities in one verse at VS 19.33 |
| horse sacrifice | `VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE` | new | MEDIUM | named at VS 18.22; the horse consecrated "for the immolation" at VS 22.19; the axe at VS 25.41; the post at VS 25.29 |
| fire-altar piling | `VG:CONCEPT:AGNI-CITI-FIRE-PILING` | new | MEDIUM | Agni addressed as `cīyamānaḥ` at VS 13.41 and VS 13.47; the bricks addressed as bricks at VS 17.2 |
| soma pressing | `VG:CONCEPT:SOMA-PRESSING` | augment | HIGH | three numbered pressings, RV 3.28 / AVS 6.47 / VS 19.26; the priestly cups, RV 2.37 |
| sacrifice | `VG:CONCEPT:YAJNA-SACRIFICE` | augment | MEDIUM | the office vocabulary of RV 2.1.2, RV 1.94.6, RV 10.91.10, RV 2.43.2 |
| agnihotra | `VG:CONCEPT:AGNIHOTRA` | augment | LOW | one passage, AVS 11.7.9, and no other |
| consecration | `VG:CONCEPT:DIKSA-CONSECRATION` | augment | MEDIUM | VS 19.30, AVS 11.7.8, AVS 12.5.3 |

### The two findings behind the new names

**The aśvamedha is in the corpus, and V2's note that it is not was defeated by a sandhi
rule V2 itself documented.** `domain_entities_material.yaml` records: *"aśvamedha — Not a
ritual node. The word's single token hit, RV 5.27.5, is the PATRON Aśvamedha."* The
reasoning about RV 5.27.5 is correct. But at **VS 18.22** the compound appears in the
"may … prosper by sacrifice" litany with its initial *a-* elided after the preceding
*me*, written `प्राणश्च मेऽश्वमेधश्च मे` and folding to `prāṇaśca me śvamedhaśca me`. No
probe of `aśvamedha` can reach it; `śvamedhaśca` reaches it exactly once, with zero
intrusions. This is the same mechanism the material header describes for `śvā` (dog vs.
*aśvā*, mare) — used there to reject an alias, and here the reason a true one was missed.

**The rite-name `agnicayana` is absent, so the node is not called that.** `agnicayana`,
`uttaravedi`, `cātvāla`, `dhiṣṇya`, `sphya`, `mekṣaṇa` and `upabhṛt` all match nothing
anywhere in the four Saṃhitās. What the corpus has is the act: `cīyamānaḥ`, "while thou art
being piled" (VS 13.41, VS 13.47), and the brick (VS 17.2). The node is named `citi`, from
the act, and its `basis` says the layers, the brick-count and the falcon shape are
Brāhmaṇa.

---

## 2. Rites refused

Every candidate from the brief, accounted for. A refusal is not a gap; it is what the file
asserts about the corpus.

| candidate | verdict | why, in one line |
|---|---|---|
| yajña | accepted (augment) | already modelled; augmented with the office vocabulary and 8 `DESCRIBED_IN` |
| soma pressing | accepted (augment) | already modelled; augmented with the only `HAS_STEP` edges in the graph |
| agnihotra | accepted (augment), LOW | the word occurs once, AVS 11.7.9; `DESCRIBED_IN` with one member is the honest shape |
| oblations | **refused** | `havis` is a material, not a procedure; `VG:CONCEPT:HAVIS-OBLATION` already exists as an `OFFERING`, and a rite node for it would make "what does this rite offer" circular |
| consecration | accepted (augment) | already modelled; augmented with its three passages |
| altar procedures | **split**: piling accepted, the rest refused | the piling is attested as an act (`cīyamānaḥ`) with a brick; the *procedures* — the layers, the trench, the northern altar — are Brāhmaṇa, and their vocabulary (`uttaravedi`, `cātvāla`, `sphya`) matches nothing |
| priestly roles | accepted | 5 new `RITUAL_ROLE` entities; see §5 |
| marriage rites | **refused as a `Ritual`** | already modelled as `VG:CONCEPT:VIVAHA-MARRIAGE`, node type `SOCIAL_RITE`; a second node would double-count it. `DESCRIBED_IN` admits `SocialRite` but `load_rituals()` matches `(rt:Ritual)`, so it cannot be given passages without a loader change — filed, not faked |
| funeral rites | **refused as a `Ritual`** | same: `VG:CONCEPT:PITRYANA-FUNERARY-RITE` is a `SOCIAL_RITE` |
| healing rites | **refused** | the Atharvavedic healing material is already carried by 12 `CONDITION` nodes and the `TREATS` predicate; a "healing rite" node would restate those edges from the other end and add no fact |
| protective rites | **refused** | same, via `PROTECTS_FROM` and `VG:CONCEPT:SARMAN-PROTECTION` |
| royal rites | **refused** | `rājasūya` 0 hits, `vājapeya` 0, `abhiṣeka` 0; `abhiṣiñcāmi` has 3 hits, all Atharvavedic and none royal. VS 9–10 and VS 22.22's prayer for the realm are real and stay reachable through `RAJAN-KINGSHIP` and the *rāṣṭra* vocabulary — the same treatment V2 gave the aśvamedha |
| domestic rites | **refused** | `gṛhapati`, the obvious hook, is an epithet of Agni in 11 of its 12 hits (see §3); house-building is already `VG:CONCEPT:SALA-HOUSE-BUILDING`, a `SOCIAL_RITE` |
| agniṣṭoma, pravargya, cāturmāsya, paśubandha, darśapūrṇamāsa, upasad, prāyaṇīya | **refused** | every one of these names matches nothing in any of the four Saṃhitās. They are the names the Brāhmaṇas and Sūtras give to programmes the Saṃhitās supply words for. A node per name would import that systematisation on the strength of a list |

---

## 3. The alias probe table

197 candidate forms measured with `scripts/probe_domain_aliases.py` against all 20,210
mantras. 40 written. Every accepted form was read in the verse that produced it with
`scripts/show_passage.py`.

### Accepted (40)

| alias | token hits (RV/SV/YV/AV) | witness read | entity |
|---|---|---|---|
| `upayāmagṛhīto` | 51 (0/0/51/0) | VS 7.4 "Taken upon a base art thou" | GRAHA-SOMA-DRAWING |
| `grahā` | 3 (0/0/2/1) | VS 9.4 "grahā ūrjāhutayaḥ"; AVS 11.7.18 "grahā haviḥ" | GRAHA-SOMA-DRAWING |
| `grahaiḥ` | 1 (0/0/1/0) | VS 19.28 "grahaiḥ stomāś ca viṣṭutīḥ" | GRAHA-SOMA-DRAWING |
| `grahān` | 1 (1/0/0/0) | RV 10.114.5 "twelve chalices of Soma" | GRAHA-SOMA-DRAWING |
| `sautrāmaṇī` | 1 (0/0/1/0) | VS 19.31 | SAUTRAMANI |
| `sautrāmaṇyā` | 1 (0/0/0/1) | AVS 3.3.2 "with the sāutrāmaṇī́ (ceremony)" | SAUTRAMANI |
| `śvamedhaśca` | 1 (0/0/1/0) | VS 18.22 | ASVAMEDHA |
| `cīyamānaḥ` | 2 (0/0/2/0) | VS 13.41, VS 13.47 | AGNI-CITI |
| `potā` | 7 (5/1/1/0) | RV 4.9.3 "Or as the Potar sits him down"; VS 19.42 | POTR-PURIFIER |
| `potram` | 2 (2/0/0/0) | RV 1.76.4, RV 10.2.2 "veṣi hotram uta potraṃ" | POTR-PURIFIER |
| `potraṃ` | 2 (2/0/0/0) | RV 2.1.2, RV 10.91.10 | POTR-PURIFIER |
| `potrāt` | 4 (1/0/0/3) | RV 2.37.2 "drink Soma … from the Potar's cup" | POTR-PURIFIER |
| `potrād` | 4 (3/0/0/1) | RV 1.15.2, RV 2.36.2, RV 2.37.4 | POTR-PURIFIER |
| `praśāstā` | 2 (2/0/0/0) | RV 1.94.6, RV 2.5.4 "as Director was he born" | PRASASTR |
| `praśāstraṃ` | 2 (2/0/0/0) | RV 2.1.2, RV 10.91.10 | PRASASTR |
| `neṣṭraṃ` | 2 (2/0/0/0) | RV 2.1.2 | NESTR |
| `neṣṭrād` | 2 (2/0/0/0) | RV 1.15.9, RV 2.37.4 | NESTR |
| `neṣṭrāt` | 1 (1/0/0/0) | RV 2.37.3 "from the Nestar's cup" | NESTR |
| `agnid` | 2 (2/0/0/0) | RV 2.1.2 "tvam agnid ṛtāyataḥ" | AGNIDH |
| `yāḍagnīt` | 1 (0/0/1/0) | VS 7.15 | AGNIDH |
| `udgāteva` | 1 (1/0/0/0) | RV 2.43.2 "thou like the chanter-priest chantest the Sama" | UDGATR |
| `prātaḥsāve` | 2 (2/0/0/0) | RV 3.28.1, RV 3.52.4 | PRATAHSAVANA |
| `prātaḥsavane` | 1 (0/0/0/1) | AVS 6.47.1 | PRATAHSAVANA |
| `prātaḥsāvas` | 1 (1/0/0/0) | RV 10.112.1 "thy first draught is early morn's libation" | PRATAHSAVANA |
| `mādhyaṃdine` | 5 (4/0/0/1) | RV 3.28.4, RV 3.32.3, RV 5.40.4 | MADHYANDINA |
| `mādhyandine` | 1 (0/0/0/1) | AVS 7.76.6 | MADHYANDINA |
| `mādhyaṃndinam` | 1 (0/0/1/0) | VS 19.26 | MADHYANDINA |
| `tṛtīyamāptaṃṃ` | 1 (0/0/1/0) | VS 19.26 "Sarasvatî obtains the third outpouring" | TRTIYA-SAVANA |
| `gṛhṇāmi` | 20 (0/0/12/8) | VS 1.10, VS 1.15, VS 5.5 "I take thee" | GRAHANA |
| `juhomi` | 28 (5/0/4/19) | VS 7.26, VS 9.38, VS 17.78 | HOMA |
| `juhota` | 11 (9/0/2/0) | VS 7.15, VS 26.22 | HOMA |
| `svāhā` | 326 (14/0/155/157) | VS 22.19, VS 25.1 "śuklāya svāhā kṛṣṇāya svāhā" | SVAHAKARA |
| `vaṣaṭkṛtaṃ` | 4 (2/0/1/1) | RV 1.162.15, VS 25.37, AVS 9.5.13 | SVAHAKARA |
| `avabhṛtha` | 3 (0/0/3/0) | VS 3.48, VS 8.27, VS 20.18 | AVABHRTHA |
| `surayā` | 5 (0/0/5/0) | VS 19.5, VS 19.33, VS 21.31 | SURA |
| `parisrutā` | 18 (0/0/18/0) | VS 20.59, VS 21.30 | PARISRUT |
| `droṇakalaśam` | 1 (0/0/1/0) | VS 19.27 | DRONAKALASA |
| `droṇakalaśāḥ` | 1 (0/0/0/1) | AVS 9.6.17 | DRONAKALASA |
| `vāyavyāni` | 2 (0/0/1/1) | VS 18.21, AVS 9.6.17 | VAYAVYA |
| `iṣṭakā` | 1 (0/0/1/0) | VS 17.2 "let these bricks be mine own milch kine" | ISTAKA |

### Rejected, with the passage that rejected it

**Rejected for contamination — the most important rejection in this pass**

| alias | hits | rejecting passage | reason |
|---|---|---|---|
| `graha` | 1 token | `VG:YV:VSM:A07:V003` | see below |
| `grahaḥ` | 1 token | `VG:YV:VSM:A07:V003` | see below |

`VG:YV:VSM:A07:V003` is **the one contaminated record in the Vājasaneyi Saṃhitā**. Its
sandhi-insensitive surface is 1,140 characters against a VSM median of **102** — eleven
times the median, and the longest of all 1,975 — and it carries Uvaṭa/Mahīdhara commentary
inline in the `source` field: `iti śeṣaḥ`, `iti śrutiḥ`, `iti pāṭhaḥ`, `yakāralopaḥ`,
`ḍalayor ekatvāt`, `ityanuvartate`. A scan of all 1,975 VSM passages for those markers
returns exactly one hit, this one.

Both token occurrences of `graha`/`grahaḥ` in the entire corpus sit inside that
commentary, and one of them sits inside the commentator's own **Brāhmaṇa quotation**:
`prāṇo vā asyaiṣa grahaḥ ... iti śrutiḥ`. Accepting `grahaḥ` as an alias would have
imported a Brāhmaṇa sentence into the Saṃhitā layer through a corpus defect — the precise
failure this project's ritual discipline exists to prevent — and it would have done so
while looking like a clean token match with 0% intrusion. **This is a defect in the corpus,
not in the probe, and it is filed for the architect: `VG:YV:VSM:A07:V003` should be split
or its commentary stripped.** Any alias whose only evidence is VS 7.3 is worthless until
then. `VG:YV:VSM:A07:V003` is deliberately excluded from the graha rite's `DESCRIBED_IN`.

**Rejected because the string names a deity, not an office**

| alias | hits | rejecting passage |
|---|---|---|
| `hotārā` | 22 (11/0/10/1) | RV 1.13.8 `hotārā daivyā kavī`, "the two Invokers … divine" — the pair the registry already carries as `VG:DEVATA:DAIVYAU-HOTARAU`. Also RV 1.142.8, RV 1.188.7, AVS 5.12.7 |
| `hotāraḥ` | 3 | AVS 5.3.5 `daivāḥ hotāraḥ`, divine hotars — 2 of 3 hits are divine (the third, RV 9.10.7's seven priests, is human) |
| `hotāro` | 3 | RV 10.128.3 `daivyā hotāro` |
| `gṛhapatiḥ` `gṛhapatim` `gṛhapatiṃ` | 12 | RV 6.15.13 `agnir hotā gṛhapatiḥ sa rājā`; RV 5.8.1, RV 5.8.2, RV 7.1.1, RV 2.1.2 — Agni in 11 of 12 |

**Rejected for the *brahman* collision** — the pair the brief warned about, and the one a
previous pass leaked fourteen passages across. Measured against the Rigveda's manual
morphological annotation, which carries the accented lemma:

| folded surface | `brahmán-` (M, the priest) | `bráhman-` (N, the formulation) | verdict |
|---|---|---|---|
| `brahmā` | 25 | 0 | safe — **already held by `VG:CONCEPT:BRAHMAN-PRIEST`** |
| `brahmāṇaḥ` | 9 | 0 | safe, unclaimed |
| `brahmāṇam` | 5 | 0 | safe, unclaimed |
| `brahmabhyaḥ` | 3 | 0 | safe, unclaimed |
| `brahmāṇā` | 1 | 0 | safe, unclaimed |
| `brahmaṇaḥ` | 2 | **54** | **rejected** — 96% wrong |
| `brahmaṇe` | 2 | 9 | rejected |
| `brahmaṇām` | 1 | 2 | rejected |
| `brahman` | 1 | 2 | rejected |
| `brahmaṇi` | 1 | 1 | rejected |
| `brahmabhiḥ` | 1 | 1 | rejected |
| | **51 total** | **254 total** | |

The five safe surfaces cover 43 of the 51 masculine tokens (84.3%) at **100% precision** —
verified not just within the `brahman` lemma but across all Rigvedic tokens: those five
folded strings resolve to `brahmán-` and to nothing else anywhere in the annotation. The
six ambiguous surfaces would have dragged in 69 formulation tokens to gain 8 priest tokens.
Full method in §5.

**A hazard found on an existing alias, which this pass cannot fix.** `brahmā` is 6
characters, so it is *eligible* for the substring pass, and its substring pass finds 231
passages whose commonest host is `brahmāṇi` — 64 occurrences of the **neuter plural**,
"prayers". In the Sāmaveda, where production runs the substring pass,
`VG:CONCEPT:BRAHMAN-PRIEST` is therefore matching *bráhman-* through its own accepted
alias. `brahmā` belongs in `SANDHI_SUPPRESSED_ALIASES`, which lives in
`src/vedagraph/enrich/concepts.py` and is outside this pass's write scope. Filed.

**Rejected for containment / homonymy**

| alias | hits | rejecting host or passage |
|---|---|---|
| `neṣṭā` | 0 token, 2 substring | 100% intrusion, host `yameneṣṭāpūrtena` |
| `agnīt` | 0 token, 1 substring | 100% intrusion, host `yāḍagnīt` — the compound form is used instead |
| `agnidh` | 0 token, 4 substring | hosts `agnidhāne`, `agnidhānāt`, `agnidhaṃ` — the fire-receptacle, not the kindler |
| `aśvamedha` | 0 token, 1 substring | host `aśvamedhasya`, RV 5.27.5, the patron |
| `śvamedha` | 0 token, 3 substring | 66.7% intrusion, hosts `aśvamedhasya` and `āśvamedhasya` |
| `surā` | 6 token, 116 substring | 47.2% intrusion; AVS 6.70.1 and RV 7.86.6 are the dicing-and-drinking topos, not an offering |
| `vāyavya` | 0 token, 3 substring | host `sakthyor vāyavyaḥ`, an anatomical term in the horse's dismemberment |
| `ukhā` | 2 token, 41 substring | 84.2% intrusion |
| `hotraṃ` | 4 token, 12 substring | 66.7% intrusion, hosts `vītihotraṃ`, `saṃhotraṃ`, `agnihotraṃ` |
| `hotre` | 3 token, 9 substring | 55.6% intrusion, hosts `śunahotreṣu`, `gnihotre` |
| `hotur` | 3 token | 25% intrusion, host `dhotur`; already held by HOTR-PRIEST anyway |
| `iṣṭim` | 0 token, 4 substring | 100% intrusion |
| `iṣṭaye` | 17 token, 51 substring | 67.3% intrusion |
| `cinvantu` | 0 token, 2 substring | 100% intrusion, host `vicinvantu` |
| `praṇītā` | 0 token, 1 substring | 100% intrusion |
| `iṣṭakāḥ` | 0 token, 1 substring | 100% intrusion |
| `badarair` | 0 token, 3 substring | 33% intrusion, host `barhirbadarairjajāna` |
| `yūpāya` | 0 token, 2 substring | 100% intrusion — but the host is `aśvayūpāya`, "for the horse's stake", and is *read evidence* for the aśvamedha's post at VS 25.29 |
| `medhaḥ` | 0 token, 1 substring | 100% intrusion |
| `kumbhī` | 4 token | AVS 11.3.11 and AVS 12.3.23 are the earth-as-cooking-pot figure — 2 of 4 wrong, so the sautrāmaṇī's liquor-jar (VS 19.16 `kumbhī surādhānī`) gets no node |
| `tṛtīye` | 18 token | AVS 6.117.3 "in the third world", AVS 6.122.4 "in the third heaven" — the third *heaven*, not the third pressing |
| `dhruva` `śukra` `ukthya` `upāṃśu` `manthin` `āśvina` | various | the *graha* names are unusable as aliases: each is an ordinary adjective or noun elsewhere (`śukra` "bright" 16 hits, `dhruva` "firm" 4). They are read evidence for VS 18.19–20, and no node claims them |

**Rejected because they match nothing anywhere in the four Saṃhitās** (probed and confirmed
zero on both passes; each is a rite, office or implement the later literature names):

`udgātā` · `udgātāraḥ` · `udgātṛ` · `udgātaram` · `udgātre` · `udgītham` · `prastotā` ·
`prastotṛ` · `pratiprasthātā` · `potṛ` · `neṣṭṛ` · `agnīdh` · `agnīdhraḥ` · `praśāstram` ·
`neṣṭram` · `potāram` · `ṛtvijyā` · `brāhmaṇaḥ` · `rājasūya` · `vājapeya` · `agniṣṭoma` ·
`agnicayana` · `pravargya` · `darśapūrṇamāsa` · `paśubandha` · `cāturmāsya` · `abhiṣeka` ·
`upasad` · `prāyaṇīya` · `agrayaṇa` · `antaryāma` · `pūtabhṛt` · `dhiṣavaṇa` · `sruva` ·
`upabhṛt` · `sphya` · `mekṣaṇa` · `dhiṣṇya` · `cātvāla` · `uttaravedi` · `trisavana` ·
`avabhṛthaḥ` · `avabhṛthena` · `avabhṛthaśca` · `mādhyandinam` · `prātaḥsavaḥ` ·
`prokṣitam` · `medhena` · `surāvantam` · `svadhitiś` · `yūpaṃ` · `yūpam` · `tṛtīyamāptaṃ`

Three of these deserve a note. `udgātṛ` and its four inflections match nothing, but the
office *is* attested — see §5. `pūtabhṛt` and `dhiṣavaṇa` match nothing in their bare stems
yet both are read in the VS 18.21 inventory inside `-ś ca` tokens; they get no node for the
reason in the next section. `agnicayana` matching nothing is why the fire-piling node is
called `citi`.

### The sandhi pass runs on the Sāmaveda only

A finding that changed three entries and should change how this registry is authored in
future. `scripts/probe_domain_aliases.py` reports the substring pass for all four Vedas as
a diagnostic. Production does not run it that way:

```python
# src/vedagraph/enrich/concepts.py
SANDHI_MATCH_VEDAS: Final[frozenset[str]] = frozenset({"SV"})
```

So **an alias whose evidence is substring-only in the RV, YV or AV contributes nothing to
the graph.** Measured with `assign_concepts`, three of my first-draft entities were affected
and one reached zero passages:

- `cinvānas` (5 YV substring hits, 0% intrusion, real) — inert. Removed from
  `AGNI-CITI`'s aliases; the evidence stays in the definition prose.
- `droṇakalaśa` (2 YV substring hits) — inert. Removed; `droṇakalaśam` and `droṇakalaśāḥ`
  carry the entity.
- `tṛtīyaṃsavana`, `tṛtīyesavane`, `tṛtīyesavana` — all inert, and the entity reached **0
  passages**. This is not an accident of encoding: **the third pressing is the only one of
  the three the corpus never writes as a single word.** The morning has `prātaḥsāva`, the
  midday has `mādhyaṃdina`; the third has only the phrase *tṛtīya* + *savana*, in all six
  of its attestations. The one usable alias is VS 19.26's single token `tṛtīyamāptaṃṃ`.
- `pūtabhṛt`, `ādhavanīya` and `dhiṣavaṇa` get no node for the same reason: their only
  attestation is inside a `-ś ca` token in the VS 18.21 inventory, unreachable in
  production.

**A second corpus defect, filed.** `tṛtīyamāptaṃṃ` and `vaiśvadevaṃṃ` in VS 19.26 carry a
**doubled anusvāra**, an artefact of this corpus's VSM transliteration (Devanāgarī
`ᳪं᳭`). The alias is brittle by construction and will break if that transliteration is
normalised. It is used because it is the actual token and it reaches the one verse that
names all three pressings; it is flagged in the entity's definition.

---

## 4. Coverage delivered

Every one of the 21 entities reaches at least one passage under the production matcher.
503 new `MENTIONS_ENTITY` edges.

| entity | RV | SV | YV | AV | total |
|---|---:|---:|---:|---:|---:|
| SVAHAKARA-OFFERING-CALL | 15 | 0 | 152 | 150 | **317** |
| GRAHA-SOMA-DRAWING | 1 | 0 | 53 | 1 | **55** |
| HOMA-POURING-INTO-FIRE | 14 | 0 | 6 | 17 | 37 |
| GRAHANA-RITUAL-TAKING-UP | 0 | 0 | 12 | 8 | 20 |
| POTR-PURIFIER | 10 | 1 | 1 | 4 | 16 |
| PARISRUT-FERMENTED-DRAUGHT | 0 | 0 | 14 | 0 | 14 |
| MADHYANDINA-SAVANA | 4 | 0 | 1 | 2 | 7 |
| NESTR-LEADER | 5 | 0 | 0 | 0 | 5 |
| PRATAHSAVANA | 3 | 0 | 0 | 2 | 5 |
| SURA-SPIRITUOUS-LIQUOR | 0 | 0 | 5 | 0 | 5 |
| PRASASTR-DIRECTOR | 4 | 0 | 0 | 0 | 4 |
| AGNIDH-FIRE-KINDLER | 2 | 0 | 1 | 0 | 3 |
| AVABHRTHA-CONCLUDING-BATH | 0 | 0 | 3 | 0 | 3 |
| AGNI-CITI-FIRE-PILING | 0 | 0 | 2 | 0 | 2 |
| DRONAKALASA-WOODEN-TUB | 0 | 0 | 1 | 1 | 2 |
| SAUTRAMANI | 0 | 0 | 1 | 1 | 2 |
| VAYAVYA-VAYU-CUP | 0 | 0 | 1 | 1 | 2 |
| ASVAMEDHA-HORSE-SACRIFICE | 0 | 0 | 1 | 0 | 1 |
| ISTAKA-BRICK | 0 | 0 | 1 | 0 | 1 |
| TRTIYA-SAVANA | 0 | 0 | 1 | 0 | 1 |
| UDGATR-CHANTER | 1 | 0 | 0 | 0 | 1 |

Two caveats a reader should have. First, the totals are *lower* than the probe counts for
crowded entities — `parisrutā` token-matches 18 passages and lands 14; `svāhā` matches 326
and lands 317 — because `MAX_CONCEPTS_PER_PASSAGE` drops the lowest-scoring concepts on
passages that already carry many. Nine `svāhā` passages and four `parisrut` passages are
lost that way, and the loss is in the matcher, not in the evidence. Second, the shape of
this table is itself the finding the scorecard was pointing at: **the procedural vocabulary
is overwhelmingly Yajurvedic and Atharvavedic.** `svāhā` is 155 YV / 157 AV against 14 RV
and *zero* SV; `gṛhṇāmi` is 12 YV / 8 AV / 0 RV; `parisrut` and `upayāmagṛhīto` are 100%
Yajurvedic. A graph that models ritual from the Rigveda alone will systematically miss the
words spoken while things are done.

---

## 5. Priestly roles: the hotṛ, the udgātṛ, and the two *brahman*

The evaluator found two specific defects. Both are resolved, one of them by naming a
blocker rather than clearing it.

### `hotṛ` — untyped, and it stays untyped, for a one-field reason

The 321 mentions are real: `hotā` token-matches **213** passages (132 RV / 21 SV / 48 YV /
12 AV), `hotāraṃ` 43 and `hotāram` 33. All three are already held by
`VG:CONCEPT:HOTR-PRIEST` in `data/registry/concepts.yaml`, whose declaration is:

```yaml
  - concept_id: VG:CONCEPT:HOTR-PRIEST
    node_type: CONCEPT          # <- this is the entire defect
    aliases_sa: [hotā, hotāraṃ, hotāram, hotur, hotre, hotrāt, ṛtvijam, ṛtvijaḥ,
                 adhvaryuḥ, adhvaryavaḥ, adhvaryo]
```

`PERFORMED_BY`'s signature is `(Ritual -> RitualRole)`. A `Concept`-labelled node cannot be
its object, so `load_rituals()`' per-label `MATCH` finds nothing and the row lands
**silently**. That is why the corpus's most-named officiant appears in no `PERFORMED_BY`
edge in `rituals.yaml`, and it is why the scorecard read the office as untyped: it is
typed, as the wrong thing.

**This could not be fixed additively.** `load_concepts()` raises when one folded alias is
claimed by two concepts — *"an alias shared by two concepts is decided by file order, not
by evidence"* — so a second `hotṛ` node in my file would not add an office; it would stop
the merged registry loading. I verified that the merged 184-entity registry loads only
because I claim no string `HOTR-PRIEST` holds.

The fix is one field on one existing line, and it is filed rather than performed because
`data/registry/concepts.yaml` is outside this pass's write scope:

```
data/registry/concepts.yaml, VG:CONCEPT:HOTR-PRIEST:  node_type: CONCEPT -> RITUAL_ROLE
```

and then, in `rituals_v3.yaml`, adding `VG:CONCEPT:HOTR-PRIEST` to the `performed_by` of
`SAUTRAMANI` (VS 21.30, VS 21.31, VS 21.58 — the sautrāmaṇī's formulary is built on the
phrase `hotā yakṣat`, "let the Hotar worship"), `GRAHA-SOMA-DRAWING` (RV 2.37.1, "drink
Soma with the Ṛtus from the Hotar's cup") and `YAJNA-SACRIFICE` (RV 2.1.2, RV 1.94.6). All
five citations are read and are in this report.

**One thing must be decided at the same time, not later.** That node's alias list is a
portmanteau of three offices: six *hotṛ* forms, two *ṛtvij* forms (any officiant), and
three *adhvaryu* forms — an office that already has its own `RITUAL_ROLE` node in
`domain_entities_material.yaml`, holding `adhvaryavo` and `adhvaryubhiḥ`. Retyping without
splitting produces a `RitualRole` that answers "which rites does the adhvaryu officiate at"
twice, differently. That is also why I authored no separate `ṛtvij` node: its two principal
forms are inside this portmanteau, and a node built from the leftover `ṛtvijo` would be a
node built from another node's remainder.

### `udgātṛ` — absent as a stem, present once as a word

`domain_entities_material.yaml` records: *"There is deliberately no udgātar node: udgātā and
udgātāraḥ match nothing in any of the four Saṃhitās."* That is true of those two forms, and
of `udgātṛ`, `udgātaram` and `udgātre`, all of which I probed to zero.

The office is nevertheless in the corpus. The Rigveda's manual morphological annotation has
**one** token of lemma `udgātár-`:

```
passage_key    VG:RV:SAK:M02:S043:V002
surface_form   udgātā́
lemma_label    udgātár-
case NOM  number SG  gender M   part_of_speech "nominal stem"
```

The reason no probe found it is sandhi with the following word: RV 2.43.2 reads
`udgāteva śakune sāma gāyasi` — *udgātā* + *iva*, "thou like the chanter-priest chantest
the Sāman" (Griffith). `udgāteva` token-matches that one passage with zero intrusions, and
`VG:CONCEPT:UDGATR-CHANTER` is authored on it.

Two things a reader must not lose. The attestation is a **simile**: the corpus does not say
a priest chanted, it says a bird sang like one. And the office does not occur in the
**Sāmaveda** — the collection whose chant it exists to sing — at all. A single-mention
`RitualRole` is the honest shape of the udgātṛ in the Saṃhitās, and it is worth writing
precisely because a reader who sees the office missing will supply it from the Brāhmaṇas.

### Keeping the two *brahman* apart

Method, so it can be re-run:

1. Load the Rigveda's manual annotation (`vedagraph.enrich.morphology.load_annotation`) and
   take `by_lemma["brahman"]` — 305 tokens, because normalisation has already collapsed the
   accent.
2. Split on `lemma_label`, which preserves it: **`bráhman-` 254 (all `gender=N`)** and
   **`brahmán-` 51 (all `gender=M`)**. The split is clean; no token is ambiguous *at the
   lemma level*.
3. Push each token's `surface_form` through the registry's own `fold_alias` and cross-tabulate
   folded surface against lemma label. This is the step that matters, because the matcher
   sees folded surfaces, not lemmas. Six surfaces are ambiguous; the full table is in §3.
4. Keep only surfaces with zero neuter tokens, then **verify them against every token in the
   annotation, not just against the `brahman` lemma** — because a surface can be clean
   within one lemma and collide with another. `brahmā`, `brahmāṇam`, `brahmāṇaḥ`,
   `brahmāṇā` and `brahmabhyaḥ` resolve to `brahmán-` and to nothing else, anywhere.

Result: 43 of 51 masculine tokens recovered at 100% precision, and the 69 neuter tokens
sitting behind the six ambiguous surfaces excluded. `brahmaṇaḥ` alone would have brought 54
"formulation" passages into the priest node to gain 2 priest passages — the exact leak the
brief describes, and the reason it must be measured per surface rather than per lemma.

This is why `VG:CONCEPT:BRAHMAN-PRIEST` gets no new aliases from me even though four safe
ones are unclaimed: the node already holds `brahmā`, which covers 25 of the 43, and adding
to an existing entity is an edit to a sealed file. The four unclaimed safe surfaces
(`brahmāṇam`, `brahmāṇaḥ`, `brahmāṇā`, `brahmabhyaḥ` — 18 further tokens) are filed as an
available, measured improvement.

### The office vocabulary, and the fact that Agni holds most of it

Five new `RITUAL_ROLE` entities: `POTR-PURIFIER`, `PRASASTR-DIRECTOR`, `NESTR-LEADER`,
`AGNIDH-FIRE-KINDLER`, `UDGATR-CHANTER`. `RitualRole` goes from 5 to 10.

They are attached to `VG:CONCEPT:YAJNA-SACRIFICE` rather than to any particular rite,
because that is where the corpus puts them. **RV 2.1.2** is the master verse and names six
offices in one breath:

> `tavāgne hotraṃ tava potram ṛtviyaṃ tava neṣṭraṃ tvam agnid ṛtāyataḥ | tava praśāstraṃ`
> `tvam adhvarīyasi brahmā cāsi gṛhapatiś ca no dame`
>
> "Thine is the Herald's task and Cleanser's duly timed; Leader art thou, and Kindler for
> the pious man. Thou art Director, thou the ministering Priest: thou art the Brahman, Lord
> and Master in our home."

**RV 1.94.6** is its twin (`tvam adhvaryur uta hotāsi pūrvyaḥ praśāstā potā januṣā
purohitaḥ`) and RV 10.91.10 repeats RV 2.1.2 verbatim.

And in every one of those verses the holder of the office is **Agni**. The corpus's fullest
statement of the priestly establishment is a hymn telling a god that he is all of it. The
`PERFORMED_BY` edges therefore assert *that the office belongs to the sacrifice*, not that
a named human held it, and every definition in
`domain_entities_ritual_v3.yaml` says so. The places where a human does the work are
RV 1.15.2, RV 2.36.2 and RV 2.37.1–4 (the cups drawn from the Hotar's, Potar's and Nestar's
stations, and the Atharvavedic parallels at AVS 20.2 and AVS 20.67) and VS 26.22
(`neṣṭrād ṛtubhir iṣyata`); those are cited on `GRAHA-SOMA-DRAWING`, which is the rite in
which the drawing happens.

---

## 6. Three Yajurvedic rites, worked end to end

The Vājasaneyi Saṃhitā (`VG:WORK:YV:VSM`, 1,975 mantras) is the sacrificial formulary: the
actual words spoken while doing things. Each rite below answers the seven questions from
the brief, with cited passages.

### 6.1 The drawing of the soma cups — `VG:CONCEPT:GRAHA-SOMA-DRAWING`

The strongest procedural entity in the graph, and the one that most vindicates treating the
VSM as a procedural corpus: its defining formula occurs 51 times and **not once outside the
Yajurveda**.

| question | answer | passage |
|---|---|---|
| **What is used?** | ladles, cups, Vāyu vessels, the wooden tub, the pressing stones, the altar, the sacred grass — all ten in one inventory verse; the strainer from a second | VS 18.21 `srucaś ca me camasāś ca me vāyavyāni ca me droṇakalaśaś ca me grāvāṇaś ca me dhiṣavaṇe ca me pūtabhṛc ca ma ādhavanīyaś ca me vediś ca me barhiś ca me`; VS 7.26 |
| **Which deity is invoked?** | Indra, Vāyu, Mitra-Varuṇa, the Aśvins — and not by inference: the cups carry their deities in their own names | VS 18.19 `aindravāyavaś ca me maitrāvaruṇaś ca ma āśvinaś ca me`; VS 7.8 (`vāyava`), VS 7.9 (`mitrāvaruṇābhyāṃ`), VS 7.11 (`aśvibhyāṃ`), VS 9.4 (`indrāya tvā`) |
| **What is offered?** | the pressed soma, which these verses call an oblation outright | VS 9.4 `grahā ūrjāhutayaḥ`, "cups of strength-giving sacrifice"; AVS 11.7.18 `iḍā praiṣā grahā haviḥ` |
| **What object is manipulated?** | the cup itself, taken up on its support | VS 7.4 `upayāmagṛhīto 'sy antar yacha maghavan`, "Taken upon a base art thou" |
| **What action occurs?** | the taking (`gṛhṇāmi`) and the pouring (`juhomi`), both first person | VS 9.4 `indrāya tvā juṣṭaṃ gṛhṇāmy eṣa te yoniḥ`, "acceptable to Indra I take thee; this is thy womb"; VS 38.26 `tāvantam indra te graham ūrjā gṛhṇāmy akṣitam` |
| **What is the intended outcome?** | **nothing is claimed.** The graha formulas dedicate; they do not petition. `performed_for` is empty and the `basis` says why: VS 9.4's "mingle me with what is good, part me from evil" is a benediction appended to a formula, and one verse will not carry a purpose claim about a rite | — |
| **Which passages describe each stage?** | 15 `DESCRIBED_IN` edges: VS 7.1, 7.4, 7.8, 7.9, 7.11, 7.26, 9.4, 18.19, 18.20, 18.21, 19.27, 19.28, 38.26, RV 10.114.5, AVS 11.7.18 | — |

`VG:YV:VSM:A07:V003` is **excluded** from that list, although it is the one passage in
which the noun `graha` appears, because it is the contaminated record described in §3.

### 6.2 The sautrāmaṇī — `VG:CONCEPT:SAUTRAMANI`

| question | answer | passage |
|---|---|---|
| **What is used?** | the wooden tub | VS 19.27 `śatena droṇakalaśam kumbhībhyām ambhṛṇau` |
| **Which deity is invoked?** | Sarasvatī, the Aśvins, Indra, Agni — four deities, one verse, explicit | VS 19.33 `tena jinva yajamānaṃ madena sarasvatīm aśvināv indram agnim` |
| **What is offered?** | the liquor, the fermented draught, soma, milk, ghee, honey — six substances, one verse | VS 21.30 = VS 21.31 `surayā bheṣajaṃ meṣaḥ sarasvatī bhiṣag ... tokmabhiḥ payaḥ somaḥ parisrutā ghṛtaṃ madhu`; VS 19.5 `surayā somaḥ suta āsuto madāya` |
| **What object is manipulated?** | the liquor-jar — **and it gets no node**: `kumbhī` has 4 token hits and 2 are the earth-as-cooking-pot figure of AVS 11.3.11 and AVS 12.3.23, so a vessel claiming it would be half wrong | VS 19.16 `kumbhī surādhānī`, "the jar containing the liquor" |
| **What action occurs?** | the Hotar's worship, and the concluding bath | VS 21.31 `hotā yakṣat`; VS 20.18 `avabhṛtha nicumpuṇa` |
| **What is the intended outcome?** | healing. Not a reading: the same line calls the liquor `bheṣajam`, medicine, and Sarasvatī `bhiṣak`, physician | VS 21.31 |
| **Which passages describe each stage?** | 14 `DESCRIBED_IN` edges: VS 19.5, 19.16, 19.26, 19.30, 19.31, 19.32, 19.33, 19.42, 20.18, 20.59, 21.30, 21.31, 21.58, AVS 3.3.2 | — |

Two absences are recorded on the entry rather than filled. The **ram** (`meṣaḥ`, VS 21.31,
VS 24.38) is not attached: it has no node, and could not be attached if it had, because
`ANIMAL` appears in the range of `RECEIVES_OFFERING` (Devatā → Animal) and in no `USES_`
predicate. And the officiant the rite's own verses actually put to work is the **hotṛ** —
VS 21.30, VS 21.31 and VS 21.58 are all built on `hotā yakṣat` — who is absent from
`performed_by` for the type reason in §5, not for want of evidence.

### 6.3 The horse sacrifice — `VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE`

| question | answer | passage |
|---|---|---|
| **What is used?** | the axe, and the post | VS 25.41 `vaṅkrīr aśvasya svadhitiḥ sam eti`, "the axe goes to the horse's ribs"; VS 25.29 `yūpavraskā uta ye yūpavāhāś caṣāla ye aśvayūpāya takṣati`, "the hewers of the post … those who carve the knob for the horse's stake" |
| **Which deity is invoked?** | Sarasvatī (the tongue-tip), Varuṇa (the wild ram) — two, cited, not a survey | VS 25.1 `sarasvatyā agrajihvam`; VS 24.38 `nirṛtyai varuṇāyāraṇyo meṣaḥ` |
| **What is offered?** | the horse — **and no edge can say so.** `VG:CONCEPT:ASVA-HORSE` is `ANIMAL`, which is outside every `USES_` range in `RELATIONSHIP_SIGNATURES`. This is an ontology gap, recorded rather than worked around; the fix is a predicate and a predicate is not this pass's to add | VS 22.19 `devā āśāpālā eta devebhyo 'śvaṃ medhāya prokṣitaṃ rakṣata`, "Gods, guardians of the regions, protect this horse consecrated for the immolation" |
| **What object is manipulated?** | the horse's own body, which the formulary tells it to prepare | VS 23.15 `svayaṃ vājin tanvaṃ kalpayasva svayaṃ yajasva`, "Steed, from thy body, of thyself, sacrifice and accept thyself" |
| **What action occurs?** | consecration by sprinkling (`prokṣitam`), then apportionment part by part, then the offering-call | VS 22.19 (`prokṣitaṃ … svadhitiḥ svāhā`); VS 25.1 (the parts, ending `śuklāya svāhā kṛṣṇāya svāhā`) |
| **What is the intended outcome?** | kingship, offspring and heroes — the text's own list, in its own order | VS 22.22 `ā brahman brāhmaṇo brahmavarcasī jāyatām ā rāṣṭre rājanyaḥ śūra iṣavyo 'tivyādhī mahāratho jāyatāṃ … yuvāsya yajamānasya vīro jāyatām` |
| **Which passages describe each stage?** | 12 `DESCRIBED_IN` edges: VS 18.22, 22.19, 22.22, 23.15, 24.38, 25.1, 25.29, 25.37, 25.41, RV 1.162.6, 1.162.15, 1.162.18 | — |

Note that `VG:CONCEPT:YUPA-SACRIFICIAL-POST` holds none of the strings in VS 25.29 (its
aliases are `yūpaḥ`, `yūpe`, `yūpān`, `svaravaḥ`), so the mention layer does not reach that
verse. The `USES_OBJECT` edge stands anyway, because it is curated by entity id and rests on
the reading. That difference — a structural edge asserts about the *rite*, a mention edge
asserts about the *passage* — is the whole reason this layer exists alongside the mention
layer.

### A fourth, for the record

`VG:CONCEPT:AGNI-CITI-FIRE-PILING` answers the same seven from three verses: bricks
(VS 17.2), Agni (VS 13.41), no substance and no officiant because none of the three verses
names one, the act of piling (`cīyamānaḥ`), and a hundred years of life as the stated
outcome (VS 13.41 `śatāyuṣaṃ kṛṇuhi cīyamānaḥ`).

---

## 7. The `HAS_STEP` decision

**`HAS_STEP` is populated for exactly one rite, with three edges, and is empty everywhere
else.** The reasoning, in the order it forced itself:

**1. The brief's description of the predicate is wrong, and the correction changes the
question.** The brief says `HAS_STEP (→ Ritual)`. The ontology says:

```python
REL_HAS_STEP: (frozenset({LABEL_RITUAL}), frozenset({LABEL_ACTION})),
```

A step is therefore an **Action**, not a sub-rite. Before this pass the registry had five
`ACTION` entities — `STOMA-PRAISE`, `NAMAS-HOMAGE`, `YUDH-BATTLE`, `DANA-LIBERALITY`,
`JANMAN-BIRTH` — and not one was a ritual act. `HAS_STEP` was at zero partly because it had
nothing to point at. Seven ritual acts are added, all named by the corpus in the first
person, the imperative, or by an ordinal.

**2. Adjacency was refused.** The VSM's adhyāyas do follow ritual order, and that is a real,
citable fact about the text. It is not a step relation. An edge derived from "verse 4 comes
after verse 3" asserts of the rite what is only true of the manuscript, and once the edge
exists that difference is invisible. **No `HAS_STEP` edge in this pass is derived from
position in the text.**

**3. What was accepted is an ordinal the corpus states in words.** The three soma pressings
are numbered by the corpus itself, in three independent places, lexically rather than
positionally:

- **RV 10.112.1** calls the morning pressing the *first* draught: `prātaḥsāvas tava hi
  pūrvapītiḥ` — "thy first draught is early morn's libation."
- **AVS 6.47** is a three-verse hymn, one verse per pressing, with the ordinals spoken:
  v1 `agniḥ prātaḥsavane pātv asmān`; v2 `asmin **dvitīye** savane`, "at this **second**
  libation"; v3 `idaṃ **tṛtīyaṃ** savanaṃ kavīnām`, "this **third** libation". The deities
  change with the stage: Agni Vaiśvānara, then the Viśve Devāḥ with the Maruts and Indra,
  then the Saudhanvanas.
- **RV 3.28** runs all three across one hymn to one deity with one offering — the cake to
  Agni `prātaḥsāve` (v1), `mādhyaṃdine savane` (v4), `tṛtīye savane` (v5).
- **VS 19.26** states all three in a single verse with a deity for each: `aśvibhyāṃ prātaḥ
  savanam indreṇaindraṃ mādhyaṃndinam vaiśvadevaṃ sarasvatyā tṛtīyam āptaṃ savanam`.

The words *first*, *second*, *third*, *morning* and *midday* are in the text. The order is
read off those words.

**What these three edges claim:** that the corpus names this act as a numbered or
time-fixed stage of `VG:CONCEPT:SOMA-PRESSING`, and that `order` is the number or the time
the corpus gives it. Each edge carries `order`, `order_basis: SOURCE_STATED_ORDINAL`, its
own `basis` and its own passage list.

**What they do not claim:** that the three stages are exhaustive; that nothing happens
between them; that any other rite in the graph has stages; that the stage sequences of the
śrauta manuals — upasads, pravargya, sutyā, the avabhṛtha as an ordered programme — are in
the Saṃhitās. They are not.

**Two things stop just short of filling it further, and both are recorded on the entries
rather than rounded up:**

- **VS 19.26–31 is the corpus's clearest stated sequence** and it is *unusable as it
  stands*. It is a chain in the instrumental of means: `yajurbhir āpyante grahāḥ, grahaiḥ
  stomāś ca viṣṭutīḥ, chandobhir ukthaśastrāṇi, sāmnāvabhṛtha āpyate` (VS 19.28) and
  `vratena dīkṣām āpnoti, dīkṣayāpnoti dakṣiṇām, dakṣiṇayā śraddhām āpnoti, śraddhayā
  satyam āpyate` (VS 19.30). Genuine source-stated sequence — but its links are grahas,
  stomas, metres, vows and virtues, and of the eight only two exist as nodes. Filling it
  needs an `ACTION` entity per link, each probed and read. That is the next pass's work and
  it is the single highest-value thing left in this dimension.
- **RV 2.37 numbers the priestly cups**: the Hotar's (v1), the Potar's (v2), the Nestar's
  (v3), and then `turīyaṃ pātram`, the **fourth** cup (v4). Another stated ordinal, and it
  would make four steps of `GRAHA-SOMA-DRAWING` — except that RV 2.37.4 does not name the
  fourth cup, and three steps plus an unnamed fourth is not a sequence I can defend.

The same reasoning is why `DIKSA-CONSECRATION` gets no `HAS_STEP` despite VS 19.30 being an
explicit chain: `VG:CONCEPT:VRATA-ORDINANCE` is `CONCEPT` and
`VG:CONCEPT:DAKSINA-PRIESTLY-GIFT` is `OFFERING`, so `HAS_STEP`'s `Action` range cannot
reach either. The sequence is real, cited, and unrepresentable. Recording that is more
useful than an edge bent to fit.

---

## 8. `DESCRIBED_IN`: populated, and how

**0 → 71 edges**, over 8 rites (68 distinct passages). Every one is a passage key that was
resolved against `load_corpus` — 88 references, 73 distinct keys, zero missing — and, more
importantly, **every one was read** — printed with `scripts/show_passage.py` and
judged, translation included where the corpus has one.

| rite | edges |
|---|---:|
| GRAHA-SOMA-DRAWING | 15 |
| SOMA-PRESSING (augment) | 15 |
| SAUTRAMANI | 14 |
| ASVAMEDHA-HORSE-SACRIFICE | 12 |
| YAJNA-SACRIFICE (augment) | 8 |
| AGNI-CITI-FIRE-PILING | 3 |
| DIKSA-CONSECRATION (augment) | 3 |
| AGNIHOTRA (augment) | 1 |

`AGNIHOTRA` having exactly one is the point of the edge, not a failure of it. AVS 11.7.9 is
the only verse in the four Saṃhitās that names the rite, and a `DESCRIBED_IN` list with one
member says so where an empty one would look like an unfinished job.

**What is not here.** `DESCRIBED_IN`'s signature already admits `SocialRite`, so the four
`SOCIAL_RITE` entities in `domain_entities_concern.yaml` — `VIVAHA-MARRIAGE`,
`PRASUTI-CHILDBIRTH`, `PITRYANA-FUNERARY-RITE`, `SALA-HOUSE-BUILDING` — are the obvious next
candidates. They are absent because `load_rituals()` matches `(rt:Ritual {entity_key: ...})`
and rows for them would land nothing while looking loaded. Widening that `MATCH` is the
architect's call; putting the rows in first would be the kind of silent zero this repository
has been bitten by before.

---

## 9. What must be merged, and by whom

`rituals_v3.yaml` is additive and `rituals.yaml` is untouched. Four things need the
architect, and none of them is inside this pass's write scope.

1. **`_RITUAL_EDGES` has no entry for `has_step` or `described_in`,** so nothing reads them
   today. `described_in` fits the existing tuple shape as
   `("described_in", "DESCRIBED_IN", ("Passage",))`. `has_step` deliberately does not: it is
   a list of mappings, because a step relation that cannot carry its order is not worth
   writing, and `order` / `order_basis` / `passages` have to land on the edge.
2. **`VG:CONCEPT:HOTR-PRIEST` needs `node_type: RITUAL_ROLE`,** and its alias list needs
   splitting from the adhvaryu's. §5.
3. **`brahmā` needs adding to `SANDHI_SUPPRESSED_ALIASES`** in
   `src/vedagraph/enrich/concepts.py`: it is matching the neuter plural `brahmāṇi`,
   "prayers", 64 times on the substring pass, in the one Veda where production runs it. §3.
4. **`VG:YV:VSM:A07:V003` should be split or its commentary stripped.** It is the one VSM
   passage carrying Uvaṭa/Mahīdhara commentary in its `source` field, it is 11× the VSM
   median length, and it is the sole evidence for two aliases this pass therefore refused.
   §3.

`augment`-mode entries name only the keys this pass has new evidence for; every other key is
**absent rather than empty**, so a concatenating merge cannot overwrite a V1 list with a
shorter one. An absent key means "not restated here"; an empty list means "the corpus does
not support one". Those are different facts and the file distinguishes them.

---

## 10. What a researcher must not conclude from this layer

Read in the wrong direction, this layer will support statements the corpus does not make.
Six of them, explicitly:

1. **Not that these are all the rites, nor that a rite absent here is absent from Vedic
   religion.** Eight rites are what the *Saṃhitā text* supports at this evidence standard.
   The agniṣṭoma, the rājasūya, the pravargya and the cāturmāsya are absent because their
   **names** are absent — and their material is often present. The refusals in §2 are
   statements about vocabulary, not about religion.

2. **Not that a `PERFORMED_BY` edge means a human being did the work.** In the verses that
   supply almost the whole office vocabulary — RV 2.1.2, RV 1.94.6, RV 10.91.10 — the potṛ,
   the neṣṭṛ, the praśāstṛ, the agnīdh, the adhvaryu and the brahman are all **Agni**. The
   edge says the office belongs to the sacrifice. It does not say who held it.

3. **Not that the hotṛ has no role in these rites.** He is the corpus's most-named
   officiant, at 321 mentions, and he appears in no `PERFORMED_BY` edge because of one
   mistyped field, documented in §5. Absence from this layer is not absence from the
   corpus, and this is the case where the difference is largest.

4. **Not that the three `HAS_STEP` edges are a ritual programme.** They are three stages the
   corpus numbers with its own words for one rite. They do not exhaust the soma day, they do
   not imply that other rites in the graph are unordered, and nothing in this graph
   represents the ordered sequences of the śrauta manuals. §7.

5. **Not that a passage-count is an importance measure, or that the Rigveda is the ritual
   Veda.** The procedural vocabulary is Yajurvedic and Atharvavedic: `svāhā` is 155 YV /
   157 AV against 14 RV and **zero** SV; `upayāmagṛhīto` and `parisrut` are 100%
   Yajurvedic; `gṛhṇāmi` is 0% Rigvedic. And the counts in §4 are *lower* than the true
   attestation for crowded entities because `MAX_CONCEPTS_PER_PASSAGE` drops concepts from
   passages that already carry many. Nine `svāhā` passages and four `parisrut` passages are
   missing for that reason alone.

6. **Not that the aśvamedha node describes the horse sacrifice as the tradition knows it.**
   VS 22–25 gives a consecrated horse, an axe, a post, an apportionment and a prayer for
   the realm. The year-long release of the horse, the three pressing days, the queens and
   the identification of the horse with the year are **Brāhmaṇa and Sūtra**. They were
   considered, and they are refused, and the entry says so. The same applies to the
   agnihotra's twice-daily milk (one verse of evidence, LOW confidence), to the
   agnicayana's five layers and 10,800 bricks (three verses of evidence), and to the
   dīkṣā's programme of observances (a position in a sequence, and no procedure).

The single sentence to carry away: **every empty list in these two files is an assertion,
and it is the assertion that took the most work.**
