# Material culture and ritual lexicon, V1

Two data files, audited alias by alias:

* `data/domain/vedagraph_domain_v2/domain_entities_material.yaml` -- 45 entities, 157
  Sanskrit aliases, 53 English aliases.
* `data/domain/vedagraph_domain_v2/rituals.yaml` -- 4 rituals, each with a stated basis.

Entities by node type: ANIMAL 7, CROP 5, METAL 4, OBJECT 8, RITUAL 2, RITUAL_ROLE 5,
RIVER 6, TRIBE 5, WEAPON 3. That is the full 45-entity authoring budget. With the 89
concepts already in `data/registry/concepts.yaml` and the 29 in the sibling fragment
`domain_entities_concern.yaml` the merged V2 registry comes to 163 entities, inside
`MAX_CONCEPT_NODES`, which Knowledge Model V2 raised from 150 to 260 while this audit was
running.

Reach: the Sanskrit token pass hits 1,023 mantra-alias pairs and the English pass
1,132, across all four Vedas. The Samaveda is reached by Sanskrit only, because it
has no translations.

## Method, and why it is per alias

Three passes, in this order.

1. **Sweep.** 370 candidate Sanskrit forms and 95 candidate English tokens were measured
   against all 20,210 mantras -- token hits per Veda, substring hits per Veda, and the host
   word of every substring hit. 4 Sanskrit and 10 English candidates were added and
   measured afterwards (ajam, turvasam, rajasuyam, ajaya; household-priest, adhvaryus, the
   tribe names).
2. **Read the witness.** For every candidate that survived the sweep, one matched passage
   per Veda was printed with its translation and judged by hand. This pass did the real
   work: `ajah` and `ajasya` have similar statistics and opposite verdicts, because the
   witnesses for the second are RV 1.164.6 "the Unborn's image" and RV 10.82.6 "the
   Unborn's navel".
3. **Verify.** `scripts/probe_domain_aliases.py --file ... --collisions` over the final
   Sanskrit list reports *none of the 157 probed aliases collide* with the existing
   registry -- 157 because `svanam` was cut after that run, on its own evidence. A
   throwaway assertion script then checked, without eyeballing: every `concept_id` matches
   `^VG:CONCEPT:[A-Z0-9]+(?:-[A-Z0-9]+)*$`; every `broader`, `related_devatas` and ritual
   key resolves; no alias is claimed twice inside the file, against `concepts.yaml`, or
   against the sibling fragment `domain_entities_concern.yaml`; and every ritual field
   satisfies `RELATIONSHIP_SIGNATURES` -- `performed_by` targets carry the RitualRole
   label, `uses_substance` targets carry Substance or Plant, and so on. All assertions
   pass.

The intrusion share below is measured over the substring pass, which the matcher runs on
the **Samaveda only**. Under six folded characters that pass is blocked outright, so a high
intrusion share there is harmless and is reported anyway; above it, the "SV substring"
column is the number of Samavedic mantras the alias reaches without a word boundary, and
that is the only place a containment error can become an assertion.

## Committed Sanskrit aliases

Token hits per Veda from `scripts/probe_domain_aliases.py`. "Substring intrusion" is the
share of that alias's substring hits whose host word does not begin with the alias.

**YAVA-BARLEY** (CROP)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| yavaṃ | yavaṃ | 5 | 11 | 1 | 2 | 4 | 18 | 36% | blocked (<6) | KEPT |
| yavam | yavam | 5 | 2 | 0 | 0 | 3 | 5 | 26% | blocked (<6) | KEPT |
| yavena | yavena | 6 | 4 | 0 | 0 | 4 | 8 | 0% | 1 hit(s) | KEPT |
| yavasya | yavasya | 7 | 2 | 0 | 0 | 2 | 4 | 20% | 0 hit(s) | KEPT, watch hosts (kuyavasya) |
| yavān | yavān | 5 | 0 | 0 | 0 | 2 | 2 | 83% | blocked (<6) | KEPT |

**VRIHI-RICE** (CROP)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| vrīhim | vrīhim | 6 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| taṇḍulaḥ | taṇḍulaḥ | 8 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| taṇḍulāḥ | taṇḍulāḥ | 8 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**TILA-SESAME** (CROP)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tilam | tilam | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |
| tilasya | tilasya | 7 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| tilamiśrā | tilamiśrā | 9 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| tilamiśrāḥ | tilamiśrāḥ | 10 | 0 | 0 | 0 | 2 | 2 | 0% | 0 hit(s) | KEPT |

**MASA-BEAN** (CROP)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| māṣam | māṣam | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |
| māṣāḥ | māṣāḥ | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |

**DHANYA-GRAIN** (CROP)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| dhānyam | dhānyam | 7 | 2 | 0 | 0 | 3 | 5 | 14% | 0 hit(s) | KEPT |
| dhānyaṃ | dhānyaṃ | 7 | 0 | 0 | 0 | 4 | 4 | 0% | 0 hit(s) | KEPT |
| dhānyasya | dhānyasya | 9 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| dhānā | dhānā | 5 | 4 | 0 | 0 | 5 | 9 | 87% | blocked (<6) | KEPT |
| dhānāḥ | dhānāḥ | 6 | 6 | 0 | 1 | 0 | 7 | 83% | 1 hit(s) | KEPT, watch hosts (dadhānāḥ; yātudhānāḥ; śraddadhānāḥ) |

**AYAS-METAL** (METAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| ayasā | ayasā | 5 | 0 | 0 | 0 | 1 | 1 | 99% | blocked (<6) | KEPT |
| ayaso | ayaso | 5 | 1 | 0 | 0 | 0 | 1 | 90% | blocked (<6) | KEPT |
| ayasi | ayasi | 5 | 0 | 0 | 0 | 1 | 1 | 94% | blocked (<6) | KEPT |
| āyasam | āyasam | 6 | 4 | 0 | 0 | 0 | 4 | 69% | 2 hit(s) | KEPT, watch hosts (viśvadhāyasam; bhūridhāyasam; vāyasam) |
| āyasaḥ | āyasaḥ | 6 | 2 | 0 | 0 | 1 | 3 | 40% | 1 hit(s) | KEPT, watch hosts (jyāyasaḥ; viśvadhāyasaḥ) |
| āyasī | āyasī | 5 | 1 | 0 | 0 | 0 | 1 | 0% | blocked (<6) | KEPT |

**RAJATA-SILVER** (METAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| rajate | rajate | 6 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| rajatā | rajatā | 6 | 0 | 0 | 1 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**LOHA-COPPER** (METAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| lohaṃ | lohaṃ | 5 | 0 | 0 | 1 | 0 | 1 | 0% | blocked (<6) | KEPT |

**SISA-LEAD** (METAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| sīsaṃ | sīsaṃ | 5 | 0 | 0 | 1 | 3 | 4 | 0% | blocked (<6) | KEPT |
| sīsena | sīsena | 6 | 0 | 0 | 2 | 1 | 3 | 0% | 0 hit(s) | KEPT |

**VRSABHA-BULL** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| vṛṣabhaḥ | vṛṣabhaḥ | 8 | 16 | 0 | 0 | 1 | 17 | 0% | 0 hit(s) | KEPT |
| vṛṣabho | vṛṣabho | 7 | 51 | 8 | 4 | 15 | 78 | 0% | 8 hit(s) | KEPT |
| vṛṣabham | vṛṣabham | 8 | 6 | 0 | 1 | 1 | 8 | 0% | 0 hit(s) | KEPT |
| vṛṣabhaṃ | vṛṣabhaṃ | 8 | 26 | 8 | 2 | 8 | 44 | 0% | 8 hit(s) | KEPT |
| vṛṣabhasya | vṛṣabhasya | 10 | 12 | 0 | 2 | 1 | 15 | 0% | 0 hit(s) | KEPT |
| vṛṣabhāya | vṛṣabhāya | 9 | 12 | 0 | 1 | 4 | 17 | 0% | 0 hit(s) | KEPT |
| vṛṣabhāḥ | vṛṣabhāḥ | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| vṛṣabheṇa | vṛṣabheṇa | 9 | 2 | 0 | 0 | 0 | 2 | 0% | 0 hit(s) | KEPT |
| ukṣā | ukṣā | 4 | 7 | 3 | 3 | 0 | 13 | 63% | blocked (<6) | KEPT |
| anaḍvān | anaḍvān | 7 | 0 | 0 | 0 | 8 | 8 | 14% | 0 hit(s) | KEPT |

**AJA-GOAT** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| ajaḥ | ajaḥ | 4 | 3 | 0 | 1 | 9 | 13 | 82% | blocked (<6) | KEPT |
| ajam | ajam | 4 | 0 | 0 | 0 | 2 | 2 | 98% | blocked (<6) | KEPT |
| ajām | ajām | 4 | 0 | 0 | 0 | 1 | 1 | 90% | blocked (<6) | KEPT |
| ajena | ajena | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |

**AVI-SHEEP** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| aviḥ | aviḥ | 4 | 0 | 0 | 0 | 1 | 1 | 99% | blocked (<6) | KEPT |
| avim | avim | 4 | 0 | 0 | 0 | 1 | 1 | 93% | blocked (<6) | KEPT |
| avīnām | avīnām | 6 | 2 | 0 | 0 | 0 | 2 | 84% | 1 hit(s) | KEPT, watch hosts (kavīnām; hiraṇyavīnām) |
| avyā | avyā | 4 | 2 | 2 | 0 | 0 | 4 | 96% | blocked (<6) | KEPT |
| avye | avye | 4 | 12 | 6 | 0 | 0 | 18 | 67% | blocked (<6) | KEPT |
| avyaye | avyaye | 6 | 9 | 3 | 0 | 0 | 12 | 0% | 3 hit(s) | KEPT |
| ūrṇā | ūrṇā | 4 | 1 | 0 | 0 | 0 | 1 | 80% | blocked (<6) | KEPT |
| meṣaḥ | meṣaḥ | 5 | 0 | 0 | 2 | 0 | 2 | 0% | blocked (<6) | KEPT |
| meṣam | meṣam | 5 | 3 | 0 | 0 | 0 | 3 | 0% | blocked (<6) | KEPT |
| meṣī | meṣī | 4 | 0 | 0 | 2 | 0 | 2 | 0% | blocked (<6) | KEPT |

**SVAN-DOG** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| śvānaḥ | śvānaḥ | 6 | 0 | 0 | 0 | 2 | 2 | 0% | 0 hit(s) | KEPT |
| śunaḥ | śunaḥ | 5 | 1 | 0 | 0 | 0 | 1 | 0% | blocked (<6) | KEPT |
| śunā | śunā | 4 | 0 | 0 | 0 | 1 | 1 | 47% | blocked (<6) | KEPT |

**MAHISA-BUFFALO** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| mahiṣaḥ | mahiṣaḥ | 7 | 2 | 1 | 0 | 8 | 11 | 0% | 1 hit(s) | KEPT |
| mahiṣam | mahiṣam | 7 | 2 | 0 | 0 | 0 | 2 | 0% | 0 hit(s) | KEPT |
| mahiṣaṃ | mahiṣaṃ | 7 | 3 | 1 | 1 | 1 | 6 | 0% | 1 hit(s) | KEPT |
| mahiṣā | mahiṣā | 6 | 9 | 2 | 2 | 0 | 13 | 0% | 2 hit(s) | KEPT |
| mahiṣasya | mahiṣasya | 9 | 6 | 1 | 1 | 0 | 8 | 0% | 1 hit(s) | KEPT |

**MANDUKA-FROG** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| maṇḍūkā | maṇḍūkā | 7 | 3 | 0 | 0 | 1 | 4 | 0% | 0 hit(s) | KEPT |
| maṇḍūkāḥ | maṇḍūkāḥ | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| maṇḍūkam | maṇḍūkam | 8 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**MRGA-WILD-BEAST** (ANIMAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| mṛgaḥ | mṛgaḥ | 5 | 3 | 0 | 0 | 6 | 9 | 10% | blocked (<6) | KEPT |
| mṛgo | mṛgo | 4 | 11 | 2 | 3 | 4 | 20 | 5% | blocked (<6) | KEPT |
| mṛgam | mṛgam | 5 | 1 | 0 | 0 | 1 | 2 | 0% | blocked (<6) | KEPT |
| mṛgāḥ | mṛgāḥ | 5 | 0 | 0 | 0 | 2 | 2 | 0% | blocked (<6) | KEPT |
| mṛgasya | mṛgasya | 7 | 4 | 0 | 0 | 1 | 5 | 0% | 0 hit(s) | KEPT |
| mṛgāya | mṛgāya | 6 | 1 | 0 | 0 | 1 | 2 | 0% | 0 hit(s) | KEPT |
| mṛgāṇām | mṛgāṇām | 7 | 2 | 0 | 0 | 0 | 2 | 0% | 0 hit(s) | KEPT |

**PASA-NOOSE** (WEAPON)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| pāśaḥ | pāśaḥ | 5 | 0 | 0 | 1 | 0 | 1 | 50% | blocked (<6) | KEPT |
| pāśam | pāśam | 5 | 2 | 0 | 0 | 4 | 6 | 11% | blocked (<6) | KEPT |
| pāśān | pāśān | 5 | 3 | 0 | 0 | 45 | 48 | 8% | blocked (<6) | KEPT |
| pāśāḥ | pāśāḥ | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |
| pāśinaḥ | pāśinaḥ | 7 | 1 | 0 | 0 | 1 | 2 | 0% | 0 hit(s) | KEPT |
| pāśaiḥ | pāśaiḥ | 6 | 0 | 0 | 0 | 1 | 1 | 50% | 0 hit(s) | KEPT, watch hosts (jyāpāśaiḥ) |
| pāśāt | pāśāt | 5 | 0 | 0 | 0 | 8 | 8 | 0% | blocked (<6) | KEPT |

**SVADHITI-AXE** (WEAPON)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| svadhitiḥ | svadhitiḥ | 9 | 2 | 0 | 1 | 0 | 3 | 0% | 0 hit(s) | KEPT |
| svadhitau | svadhitau | 9 | 1 | 0 | 1 | 0 | 2 | 0% | 0 hit(s) | KEPT |
| svadhitinā | svadhitinā | 10 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**JYA-BOWSTRING** (WEAPON)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| jyā | jyā | 3 | 1 | 1 | 0 | 1 | 3 | 57% | blocked (<6) | KEPT |
| jyām | jyām | 4 | 0 | 0 | 0 | 4 | 4 | 43% | blocked (<6) | KEPT |

**ULUKHALA-MORTAR** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| ulūkhale | ulūkhale | 8 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| ulūkhalam | ulūkhalam | 9 | 0 | 0 | 0 | 1 | 1 | 33% | 0 hit(s) | KEPT, watch hosts (mahānagnyulūkhalam) |
| ulūkhalasutānām | ulūkhalasutānām | 15 | 4 | 0 | 0 | 0 | 4 | 0% | 0 hit(s) | KEPT |
| musale | musale | 6 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**YUPA-SACRIFICIAL-POST** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| yūpaḥ | yūpaḥ | 5 | 1 | 0 | 0 | 0 | 1 | 0% | blocked (<6) | KEPT |
| yūpe | yūpe | 4 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |
| yūpān | yūpān | 5 | 0 | 0 | 0 | 1 | 1 | 0% | blocked (<6) | KEPT |
| svaravaḥ | svaravaḥ | 8 | 1 | 0 | 0 | 2 | 3 | 0% | 0 hit(s) | KEPT |

**VEDI-ALTAR** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| vediḥ | vediḥ | 5 | 2 | 0 | 2 | 3 | 7 | 0% | blocked (<6) | KEPT |
| vedim | vedim | 5 | 2 | 0 | 0 | 0 | 2 | 0% | blocked (<6) | KEPT |
| vediṃ | vediṃ | 5 | 3 | 0 | 0 | 4 | 7 | 0% | blocked (<6) | KEPT |
| vedyām | vedyām | 6 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**CAMASA-CUP** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| camasaḥ | camasaḥ | 7 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| camasam | camasam | 7 | 2 | 0 | 0 | 2 | 4 | 0% | 0 hit(s) | KEPT |
| camasā | camasā | 6 | 2 | 0 | 0 | 0 | 2 | 0% | 0 hit(s) | KEPT |
| camase | camase | 6 | 1 | 0 | 0 | 1 | 2 | 17% | 1 hit(s) | KEPT, watch hosts (devāścamaseṣūnnīto) |

**SRUC-LADLE** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| srucaḥ | srucaḥ | 6 | 2 | 0 | 0 | 0 | 2 | 71% | 0 hit(s) | KEPT, watch hosts (yatasrucaḥ) |
| srucā | srucā | 5 | 4 | 0 | 1 | 1 | 6 | 30% | blocked (<6) | KEPT |
| sruveṇa | sruveṇa | 7 | 2 | 0 | 0 | 1 | 3 | 0% | 0 hit(s) | KEPT |

**KALASA-JAR** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| kalaśaḥ | kalaśaḥ | 7 | 2 | 0 | 0 | 2 | 4 | 0% | 0 hit(s) | KEPT |
| kalaśam | kalaśam | 7 | 1 | 0 | 0 | 0 | 1 | 50% | 0 hit(s) | KEPT, watch hosts (droṇakalaśam) |
| kalaśe | kalaśe | 6 | 13 | 3 | 0 | 2 | 18 | 0% | 5 hit(s) | KEPT |
| kalaśeṣu | kalaśeṣu | 8 | 9 | 1 | 0 | 0 | 10 | 0% | 1 hit(s) | KEPT |
| kalaśasya | kalaśasya | 9 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| kalaśā | kalaśā | 6 | 2 | 0 | 0 | 0 | 2 | 6% | 4 hit(s) | KEPT |

**PAVITRA-STRAINER** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| pavitram | pavitram | 8 | 24 | 0 | 0 | 1 | 25 | 0% | 7 hit(s) | KEPT |
| pavitre | pavitre | 7 | 30 | 19 | 2 | 0 | 51 | 0% | 20 hit(s) | KEPT |
| pavitreṇa | pavitreṇa | 9 | 2 | 0 | 11 | 3 | 16 | 0% | 0 hit(s) | KEPT |
| pavitrasya | pavitrasya | 10 | 1 | 2 | 0 | 2 | 5 | 0% | 2 hit(s) | KEPT |

**DUNDUBHI-DRUM** (OBJECT)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| dundubhiḥ | dundubhiḥ | 9 | 1 | 0 | 0 | 2 | 3 | 0% | 0 hit(s) | KEPT |
| dundubhim | dundubhim | 9 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |
| dundubhe | dundubhe | 8 | 2 | 0 | 2 | 8 | 12 | 0% | 0 hit(s) | KEPT |
| dundubhinā | dundubhinā | 10 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**GANGA-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| gaṅge | gaṅge | 5 | 1 | 0 | 0 | 0 | 1 | 0% | blocked (<6) | KEPT |

**YAMUNA-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| yamunā | yamunā | 6 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| yamune | yamune | 6 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**SARAYU-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| sarayuḥ | sarayuḥ | 7 | 2 | 0 | 0 | 0 | 2 | 0% | 0 hit(s) | KEPT |

**PARUSNI-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| paruṣṇī | paruṣṇī | 7 | 0 | 0 | 0 | 1 | 1 | 0% | 1 hit(s) | KEPT |
| paruṣṇyām | paruṣṇyām | 9 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**VIPAS-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| vipāṭ | vipāṭ | 5 | 1 | 0 | 0 | 0 | 1 | 0% | blocked (<6) | KEPT |
| vipāśam | vipāśam | 7 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**SUTUDRI-RIVER** (RIVER)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| śutudri | śutudri | 7 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**BHARATA-TRIBE** (TRIBE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| bharatāḥ | bharatāḥ | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| bharatasya | bharatasya | 10 | 3 | 0 | 0 | 1 | 4 | 20% | 0 hit(s) | KEPT, watch hosts (prāyamagnirbharatasya) |
| bharatebhyaḥ | bharatebhyaḥ | 12 | 1 | 1 | 1 | 0 | 3 | 0% | 1 hit(s) | KEPT |

**PURU-TRIBE** (TRIBE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| pūravaḥ | pūravaḥ | 7 | 4 | 0 | 0 | 1 | 5 | 0% | 0 hit(s) | KEPT |
| pūrave | pūrave | 6 | 5 | 0 | 0 | 0 | 5 | 0% | 0 hit(s) | KEPT |

**YADU-TRIBE** (TRIBE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| yadum | yadum | 5 | 5 | 0 | 0 | 0 | 5 | 0% | blocked (<6) | KEPT |
| yadave | yadave | 6 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**TURVASA-TRIBE** (TRIBE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| turvaśaṃ | turvaśaṃ | 8 | 10 | 3 | 0 | 1 | 14 | 0% | 3 hit(s) | KEPT |
| turvaśam | turvaśam | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**TRTSU-TRIBE** (TRIBE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tṛtsavaḥ | tṛtsavaḥ | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| tṛtsūnām | tṛtsūnām | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |
| tṛtsubhiḥ | tṛtsubhiḥ | 9 | 1 | 0 | 0 | 0 | 1 | 0% | 0 hit(s) | KEPT |

**AGNIHOTRA** (RITUAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| agnihotraṃ | agnihotraṃ | 10 | 0 | 0 | 0 | 1 | 1 | 0% | 0 hit(s) | KEPT |

**DIKSA-CONSECRATION** (RITUAL)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| dīkṣā | dīkṣā | 5 | 0 | 0 | 0 | 3 | 3 | 0% | blocked (<6) | KEPT |
| dīkṣām | dīkṣām | 6 | 0 | 0 | 0 | 3 | 3 | 0% | 0 hit(s) | KEPT |
| dīkṣayā | dīkṣayā | 7 | 0 | 0 | 1 | 9 | 10 | 0% | 0 hit(s) | KEPT |

**ADHVARYU-PRIEST** (RITUAL_ROLE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| adhvaryavo | adhvaryavo | 10 | 18 | 1 | 0 | 1 | 20 | 0% | 1 hit(s) | KEPT |
| adhvaryubhiḥ | adhvaryubhiḥ | 12 | 3 | 0 | 0 | 1 | 4 | 0% | 0 hit(s) | KEPT |

**BRAHMAN-PRIEST** (RITUAL_ROLE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| brahmā | brahmā | 6 | 26 | 4 | 6 | 16 | 52 | 8% | 18 hit(s) | KEPT |
| brāhmaṇam | brāhmaṇam | 9 | 0 | 0 | 0 | 2 | 2 | 25% | 1 hit(s) | KEPT, watch hosts (ārṣeyabrāhmaṇam) |
| brāhmaṇāḥ | brāhmaṇāḥ | 9 | 1 | 0 | 0 | 3 | 4 | 20% | 0 hit(s) | KEPT, watch hosts (abrāhmaṇāḥ) |
| brāhmaṇasya | brāhmaṇasya | 11 | 0 | 0 | 0 | 8 | 8 | 0% | 0 hit(s) | KEPT |

**PUROHITA-CHAPLAIN** (RITUAL_ROLE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| purohitaḥ | purohitaḥ | 9 | 7 | 1 | 3 | 4 | 15 | 0% | 1 hit(s) | KEPT |
| purohitam | purohitam | 9 | 1 | 0 | 0 | 1 | 2 | 0% | 1 hit(s) | KEPT |
| purohita | purohita | 8 | 1 | 0 | 0 | 0 | 1 | 0% | 3 hit(s) | KEPT |

**YAJAMANA-SACRIFICER** (RITUAL_ROLE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| yajamānaḥ | yajamānaḥ | 9 | 0 | 0 | 3 | 2 | 5 | 0% | 0 hit(s) | KEPT |
| yajamānam | yajamānam | 9 | 3 | 0 | 2 | 1 | 6 | 12% | 0 hit(s) | KEPT |
| yajamānasya | yajamānasya | 11 | 16 | 0 | 5 | 7 | 28 | 6% | 0 hit(s) | KEPT |
| yajamānāya | yajamānāya | 10 | 21 | 3 | 9 | 24 | 57 | 8% | 3 hit(s) | KEPT |

**BRAHMACARIN-STUDENT** (RITUAL_ROLE)

| alias | folded | chars | RV | SV | YV | AV | token total | substring intrusion | SV substring | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| brahmacārī | brahmacārī | 10 | 1 | 0 | 0 | 14 | 15 | 0% | 0 hit(s) | KEPT |
| brahmacaryeṇa | brahmacaryeṇa | 13 | 0 | 0 | 0 | 3 | 3 | 0% | 0 hit(s) | KEPT |

## Committed English aliases

Matched against Griffith (RV, YV) and Whitney (AV). Every SV cell is 0, and that is not a
measurement failure: 0 of 1,844 Samavedic mantras carry a translation, so an English alias
contributes nothing there by construction.

| alias | entity | RV | SV | YV | AV | total | verdict |
|---|---|---|---|---|---|---|---|
| adhvaryu | ADHVARYU-PRIEST | 12 | 0 | 2 | 0 | 14 | KEPT |
| adhvaryus | ADHVARYU-PRIEST | 17 | 0 | 8 | 0 | 25 | KEPT |
| altar | VEDI-ALTAR | 22 | 0 | 8 | 0 | 30 | KEPT |
| axe | SVADHITI-AXE | 22 | 0 | 3 | 0 | 25 | KEPT |
| barley | YAVA-BARLEY | 14 | 0 | 10 | 16 | 40 | KEPT |
| beans | MASA-BEAN | 0 | 0 | 1 | 3 | 4 | KEPT |
| bharatas | BHARATA-TRIBE | 7 | 0 | 1 | 0 | 8 | KEPT |
| bowstring | JYA-BOWSTRING | 4 | 0 | 3 | 2 | 9 | KEPT |
| brahmans | BRAHMAN-PRIEST | 21 | 0 | 2 | 31 | 54 | KEPT; the plural is the class of men. The singular was refused as ambiguous |
| buffalo | MAHISA-BUFFALO | 5 | 0 | 2 | 1 | 8 | KEPT |
| cup | CAMASA-CUP | 13 | 0 | 2 | 1 | 16 | KEPT |
| cups | CAMASA-CUP | 2 | 0 | 7 | 1 | 10 | KEPT; 1 AV hit is camu, the trough, not camasa |
| deer | MRGA-WILD-BEAST | 25 | 0 | 3 | 2 | 30 | KEPT; some RV hits render prsati, the Maruts' dappled team, rather than mrga -- same animal, different lexeme |
| dog | SVAN-DOG | 4 | 0 | 2 | 9 | 15 | KEPT |
| dogs | SVAN-DOG | 6 | 0 | 1 | 9 | 16 | KEPT |
| drum | DUNDUBHI-DRUM | 2 | 0 | 1 | 16 | 19 | KEPT |
| ewe | AVI-SHEEP | 0 | 0 | 5 | 4 | 9 | KEPT |
| fetters | PASA-NOOSE | 2 | 0 | 2 | 28 | 32 | KEPT; Whitney's word for pasa through the Varuna and Nirrti hymns |
| filter | PAVITRA-STRAINER | 36 | 0 | 2 | 0 | 38 | KEPT |
| frog | MANDUKA-FROG | 4 | 0 | 3 | 1 | 8 | KEPT |
| frogs | MANDUKA-FROG | 5 | 0 | 1 | 2 | 8 | KEPT |
| goat | AJA-GOAT | 10 | 0 | 14 | 42 | 66 | KEPT |
| goats | AJA-GOAT | 10 | 0 | 10 | 6 | 26 | KEPT |
| grain | DHANYA-GRAIN | 10 | 0 | 8 | 14 | 32 | KEPT; renders dhana and dhanya, not yava, for which Griffith writes barley or corn |
| grains | DHANYA-GRAIN | 3 | 0 | 4 | 11 | 18 | KEPT |
| hatchet | SVADHITI-AXE | 5 | 0 | 3 | 0 | 8 | KEPT |
| house-priest | PUROHITA-CHAPLAIN | 0 | 0 | 1 | 0 | 1 | KEPT |
| household-priest | PUROHITA-CHAPLAIN | 1 | 0 | 0 | 0 | 1 | KEPT |
| iron | AYAS-METAL | 31 | 0 | 4 | 10 | 45 | KEPT |
| ladle | SRUC-LADLE | 32 | 0 | 3 | 3 | 38 | KEPT |
| metal | AYAS-METAL | 3 | 0 | 0 | 10 | 13 | KEPT |
| mortar | ULUKHALA-MORTAR | 14 | 0 | 1 | 4 | 19 | KEPT |
| noose | PASA-NOOSE | 5 | 0 | 4 | 0 | 9 | KEPT |
| nooses | PASA-NOOSE | 1 | 0 | 0 | 0 | 1 | KEPT |
| ox | VRSABHA-BULL | 10 | 0 | 10 | 7 | 27 | KEPT; the epithet problem is in bull and steer, not in ox and oxen |
| oxen | VRSABHA-BULL | 20 | 0 | 7 | 3 | 30 | KEPT; see ox |
| pestle | ULUKHALA-MORTAR | 1 | 0 | 0 | 3 | 4 | KEPT |
| pitcher | KALASA-JAR | 8 | 0 | 1 | 0 | 9 | KEPT |
| purus | PURU-TRIBE | 6 | 0 | 0 | 0 | 6 | KEPT |
| rice | VRIHI-RICE | 2 | 0 | 6 | 7 | 15 | KEPT |
| sacrificer | YAJAMANA-SACRIFICER | 39 | 0 | 35 | 37 | 111 | KEPT |
| sesame | TILA-SESAME | 0 | 0 | 0 | 10 | 10 | KEPT |
| sheep | AVI-SHEEP | 25 | 0 | 4 | 16 | 45 | KEPT |
| sieve | PAVITRA-STRAINER | 61 | 0 | 7 | 3 | 71 | KEPT; 3 AV hits are surpa, the winnowing basket, not the soma filter |
| silver | RAJATA-SILVER | 0 | 0 | 2 | 3 | 5 | KEPT |
| snares | PASA-NOOSE | 4 | 0 | 0 | 0 | 4 | KEPT |
| spoon | SRUC-LADLE | 1 | 0 | 2 | 12 | 15 | KEPT |
| strainer | PAVITRA-STRAINER | 3 | 0 | 9 | 0 | 12 | KEPT |
| student | BRAHMACARIN-STUDENT | 0 | 0 | 0 | 23 | 23 | KEPT |
| trtsus | TRTSU-TRIBE | 7 | 0 | 0 | 0 | 7 | KEPT |
| wool | AVI-SHEEP | 21 | 0 | 4 | 1 | 26 | KEPT |
| yadu | YADU-TRIBE | 16 | 0 | 0 | 0 | 16 | KEPT |
| yadus | YADU-TRIBE | 1 | 0 | 0 | 0 | 1 | KEPT |

## Dropped candidates

### Dropped because they match nothing at all

| candidate | intended for | measurement |
|---|---|---|
| parasuh, parasum, parasuna | axe | 0 token hits in four Vedas. The corpus's axe is svadhiti; SVADHITI-AXE carries the concept instead. |
| dhanusa, dhanusi, dhanusah, dhanumsi, dhanusman | bow | 0 token hits each. The forms that do occur -- dhanuh, dhanur, dhanvana, dhanvanah -- are already claimed by VG:CONCEPT:AYUDHA-WEAPON, so a bow node had nothing left to stand on. A collision drop, not an absence. |
| udgata, udgatarah | udgatar priest | 0 token hits. The office is named in the Brahmanas; the Samhitas, including the Samaveda he sings from, do not use the word. |
| loham (final m), lohah | copper | 0 token hits. The spelling that occurs is loham with anusvara, once, at VS 18.13, and that one form is what LOHA-COPPER ships. |
| rajatam, rajatena, rajatah, rajatasya | silver | 0. RAJATA-SILVER rests on rajate and rajata. |
| ayasmayam, ayasmayah, ayasmayi, ayasih, ayasena | metal | 0 token hits, although Whitney's rendering of AVS 7.115.1 quotes ayasmaya: the word is there inside a compound the tokeniser does not split. |
| matsyah, matsyah (pl.), matsyam, matsyan | fish | 0 in all four. There is no fish node. |
| krmih (1, YV), krmim, krmin, krmayah | worm | The Atharvavedic worm hymns spell it krimi, not krmi, so this probe measured the wrong stem. Recorded as a probe error rather than an absence: a worm node is available to whoever probes krimi-. |
| bastah, bastam | he-goat | 0, although Griffith's RV 1.161.13 reads "The goat declared the hound" for basto -- another sandhi-bound form the token pass cannot see. |
| uksnah, uksanah, anaduhah | ox | 0. uksa and anadvan carry it. |
| musalam, musalah | pestle | 0; `musale` (1 hit) is kept inside ULUKHALA-MORTAR. |
| yupam, yupasya, svaru, svarum | sacrificial post | 0. |
| sruc, sruci, sruvam, juhuh | ladle | 0 token hits. `sruc` has 39 substring hits, every one inside yatasrucah or udyatasruce. |
| camasan, camasasya, camasebhih | cup | 0. |
| dronah, dronesu | soma vat | 0; dronam (1) and drone (5) exist, but no vat node was funded -- see the budget list. |
| vrihih, vrihayah, vrihin, vrihibhih, vrihinam, tandulam, tandulan, tilah, tilah (pl.), tilan, tilaih, masah, masan, dhanyani, dhanyah, dhanavantam, dhanabhih, sasyam, sasyani, apupah, purodasah, kumbhah, ukhayam, aksasah | crops, vessels | 0 token hits each. |
| ganga, yamunam, sarayau, parusnyah, sutudri (long i), asiknyam, drsadvati | rivers | 0. The river names occur in one or two inflections only, which is why several river nodes here carry a single alias. |
| druhyuh, druhyum, druhyave | Druhyu tribe | 0 in all four Vedas. Griffith's "Druhyus" at RV 1.108.8 renders a form this probe did not find, and no tribe node was created on a translation alone. |
| anavah, pancajanah, pancajanyah, turvasah, yaduh, bharatesu, bharatanam | tribes | 0. `anavah` has 4 substring hits, all inside manavah, "men". |
| agnihotram, agnihotrena, agnihotrasya, asvamedhah, asvamedham, asvamedhena, rajasuyah, vajapeyah, sattram, sattre, sattrasya, pravargyah, agnistomah, purusamedhah, gharmena | named rites | 0 token hits. The srauta rite names are almost absent from the Samhitas *as words*, which is the most important negative result in this audit. |
| adhvaryum, adhvaryave, potaram, nesta, brahmanah, brahmanan, hotari, purohitaya, ajaya | priestly offices | 0. `nesta` matches twice, both inside istapurtena. |
| sacrificial-post, chaplain, bean | English | 0 hits. Whitney writes "sacrificial post (yupa)" as a phrase, and phrase matching was deliberately never built. |

### Dropped on intrusion or homonymy, with the passage that decided it

| candidate | measurement and witness |
|---|---|
| ayas | The warned trap, confirmed: 0 token hits, 645 substring hits, hosts payasa (60), vayasa (9), prayasa (5), trayastrimsat. Never shipped. |
| ayah | 1 token hit, RV 8.2.40, where Griffith's line is about a ram and a stone-hurler and nothing metallic; 74 Samavedic substring hits inside kavayah, krstayah, rusatpayah. |
| ayo | 6 token hits, 4 of them the participle of i- "to go": AVS 7.97.1, Whitney "mayest thou go fixedly". The 2 Rigvedic hits are genuine (RV 5.62.7, "its columns are of iron") and not worth the other 4. |
| rajatam (anusvara) | 2 token hits, and RV 8.25.22 is a horse's colour -- Griffith "from Harayana a white steed". 50% wrong on two hits. |
| yava, yavah | AVS 9.2.13 reads "agnir yava indro yavah", which Whitney renders "Agni [is] a repeller, Indra a repeller": yu- "ward off", not yava "barley". `yava` is 1 of 2 wrong, `yavah` 1 of 3. Both retired; barley keeps five other forms. |
| aja (long a) | 5 token hits; 4 are the imperative of aj- "to drive" in the phrase sam aja (RV 1.174.3, RV 6.25.9). |
| ajasya | 6 token hits, 3 of them a-ja "unborn", in two of the most quoted verses in the corpus: RV 1.164.6 and RV 10.82.6 (= VS 17.30). 50% wrong, and wrong exactly where a reader will check. |
| sva (svan nom.) | 13 token hits. Because initial a- elides, asva ("horses", "mare") is spelled sva: RV 6.75.7 is Griffith's "Horses whose hoofs rain dust", VS 21.33 his "A mare with a foal". Elision, not compounding -- a failure mode the registry had not recorded. |
| svanam | 2 genuine Rigvedic token hits against 5 Samavedic substring hits inside matarisvanam, a name of Agni. Cut after the final probe run. |
| uksanam | 2 token hits against 1 Samavedic substring hit inside rbhuksanam, Indra's epithet. Dropped on the ratio. |
| mahisi, mahisim | 5 token hits, but mahisi is the buffalo cow *and* the chief queen, and the Atharvavedic hits sit in domestic contexts where the queen is at least as likely. |
| jyayah | 1 token hit, RV 10.51.6, and it is jyayas "greater" -- Griffith "mine elder brothers". |
| rstih, rstim, rstibhih, rstayah, rstih (pl.) | The spear: 9 token hits, all Rigvedic, but rsti- sits inside vrsti- "rain" at 88-92% of its substring hits, and rain is another concept in this same lexicon (VG:CONCEPT:VRSTI-RAIN). No spear node, and the cost is that "which weapons" has no spear. |
| juhva | 13 token hits, and Griffith reads the ladle as a tongue in every one checked: RV 1.61.5 "with my tongue I deck", VS 13.10 "Spread with thy tongue". juhu is the offering ladle and the flame's tongue in one word. |
| cakram | 23 token hits, but 26% of its substring hits are inside vicakrame, the perfect of kram- "to stride". No wheel node. |
| aksah | 14 token hits, including the gambler's hymn RV 10.34, against aksa "axle" and "eye" and 62% substring intrusion inside nrcaksah. A dice node would have been a good node; it needs a form that is not also an axle. |
| aryah, aryam, aryaya | 15 token hits, 60-83% substring intrusion inside varyam, paryaya, mitraryamnah. Also the wrong node type: arya is a social self-designation, not a tribe, and not a term to author quickly. |
| asvamedhasya | The only asvamedha- form that occurs, once, RV 5.27.5, and it is the patron Asvamedha -- Griffith "The gifts of Asvamedha". The rite is in the corpus; the word, as the rite, is not. |
| gharmam, gharmah | 18 token hits split between the hot milk draught (AVS 8.8.17, "The hot drink (gharma) is kindled with fire"), the cauldron (RV 1.112.7) and plain warmth (AVS 6.36.1 "unfailing heat", VS 18.50 "Heaven-like is Warmth"). Three readings, not separable on the surface. |
| sarasvati and its four other forms | 172 token hits (RV 41, SV 3, YV 44, AV 15), overwhelmingly the goddess -- Griffith's "may bright Sarasvati desire our sacrifice", Whitney's "worked in is divine Sarasvati". There is therefore **no SARASVATI-RIVER node**, which leaves the corpus's most important river out of the river set. Filing those passages under a RIVER node would re-create precisely the devata/concept confusion the registry header exists to prevent, and the ASMAN-PRESSING-STONE remedy -- widen the label until it matches what it matched -- is unavailable here, because "river and goddess" is the one label this ontology may not carry. |
| bull, bulls, steer, steers | English: 302, 52, 118, 24 hits. Griffith capitalises "Bull" and "Steer" as epithets of Indra, Agni and Soma. This is the registry's "hero" case (42% vocative epithet) with worse numbers. VRSABHA-BULL keeps ten Sanskrit forms and the English tokens ox and oxen. |
| lead | English, 139 hits, and it is the verb: Griffith's "lead this our sacrifice". SISA-LEAD therefore ships with no English alias at all. |
| die | English, 57 hits, and already claimed by VG:CONCEPT:MRTYU-DEATH. A dice node would have had to take it from death. |
| ram | English, 25 hits. Whitney parenthesises IAST inside his English, so AVS 1.17.3 "the ends have rested (ram)" matches the root ram-. 7 Atharvavedic hits are suspect on that mechanism alone. |
| jar | English, 15 hits, same mechanism: `[a-z]+` cuts Whitney's jarayu into the token `jar`, so all 5 AV hits are afterbirth, not pottery. KALASA-JAR ships `pitcher` instead. |
| corn | English, 28 hits, split between yava (RV 1.23.15 "brings corn") and dhana (RV 3.52.5 "roasted corn"), which are two different nodes here. Given to neither. |
| consecration | English, 21 hits, split between diksa (VS 4.2 "The form of Consecration and of Fervour") and rajasuya (AVS 4.8.1 "the royal consecration (rajasuya)"). Given to neither; DIKSA-CONSECRATION rests on its 16 Sanskrit hits. |
| brahman | English, 118 hits, and Whitney uses it for the neuter formulation ("incantation (brahman)") as often as for the man. It belongs to VG:CONCEPT:BRAHMAN-FORMULATION as much as to BRAHMAN-PRIEST, so neither gets it. |
| stake, post | English, 10 and 16 hits. 2 of `stake` are the gambler's stake (AVS 4.38.3, "obtain the stake (praha)"), and `post` includes doorposts and beams (AVS 3.12.6 "O beam"). Over 20% wrong, which is the threshold at which the registry retired "bow". YUPA-SACRIFICIAL-POST ships Sanskrit-only. |
| snare, fetter | English. `snare`'s AVS 8.8.18 hit is aksu, a net, not pasa; `fetter` (54 hits, 50 of them Atharvavedic) is Whitney's word for bandha as well as pasa and was not individually verified. The plurals `snares` and `fetters` were verified and kept. |
| bowl, beaker, vat | English, 33, 16 and 20 hits. Griffith uses all three for camasa, kalasa and drona indifferently, which is exactly the boundary between three nodes in this file. Given to none of them. |
| worshipper, singer, priesthood, chanter, she-goat, wether, ewes, gazelle, quiver, spear, spears, lance, lances, pan, kettle, caldron, wheel, dice, calf, calves, wolf, wolves, lion, elephant, worm, worms, copper, fish, fishes | English | Either too generic to discriminate (`singer` 213 hits, `worshipper` 160), or verified but left with no node to attach to once the budget was spent. |

### Verified, and dropped only against the 45-entity budget

These matched, were read, and are right. They lost on room, and are the first things a V2
pass should restore.

| candidate | measured | why it lost |
|---|---|---|
| ODANA-RICE-DISH | odanah 21, odanam 5, odanena 1 = 27 mantras, Atharvavedic, 9% intrusion | Better attested than three of the crops that were kept, but not on the brief's target list. Whitney's "rice-dish" is a hyphenated token, so it would have English reach too. The strongest single omission in this file. |
| TRAPU-TIN | trapu 2 (VS 18.13 "my bronze", AVS 11.3.8 "Tin [its] ash") | Verified. Both hits are in list-verses that AYAS-METAL and SISA-LEAD already reach, so it adds a metal to the answer but not a passage. |
| RAJASUYA-ROYAL-CONSECRATION | rajasuyam 2 (AVS 4.8.1, AVS 11.7.7) | Verified, and AVS 4.8 is a royal-consecration hymn. Lost because its only English rendering, `consecration`, had to be refused as ambiguous with diksa, leaving two passages. |
| VAJAPEYA, AGNISTOMA | vajapeyam 1; both names in AVS 11.7.7 | Three rite names in one verse. Three nodes resting on one passage, competing for the four slots `MAX_CONCEPTS_PER_PASSAGE` allows there. |
| DRONA-VAT | dronam 1, drone 5 | The wooden soma trough, genuinely distinct from the kalasa, but its passages largely overlap it. |
| UKHA-FIRE-PAN | ukha 2 (RV 1.162.15 and one AV hit) | The pot of the horse sacrifice. 2 hits, and 0 in the Yajurveda, where the Agnicayana ukha would be expected -- a result worth re-probing before restoring. |
| VATSA-CALF, VRKA-WOLF, SIMHA-LION, HASTI-ELEPHANT, KUMBHA-POT | vatsa- 26, vrka- 21, simha- 14, hastin- 7, kumbha- 3 | All verified. GO-CATTLE and MRGA-WILD-BEAST already answer the herd and wild-animal questions, and simha and vrka are mostly similes. |
| ISUDHI-QUIVER | isudhih 2 | Has a devata of its own (VG:DEVATA:ISUDHIH) and no room. |
| TURVASA, English | Griffith writes "Turvasa" | Not probed before the budget closed. TURVASA-TRIBE ships Sanskrit-only; `turvasa` and `turvasas` should be measured for it. |
| river names, English | ganga, yamuna, parusni, sutudri, vipas, sarayu as English tokens | Not probed. Griffith's RV 10.75.5 reads "O Ganga, Yamuna, O Sutudri, Parusni and Sarasvati", so these are single lower-cased tokens and would roughly double the very thin river coverage. The clearest cheap win left on the table. |

### Dropped by another author's file, not by measurement

| candidate | what happened |
|---|---|
| VARMAN-ARMOUR | Authored here (varma 38, varmani 5, English armour and mail) and, independently, in the sibling fragment `domain_entities_concern.yaml` under the same `concept_id`, the same OBJECT type and the same related deity. The merge refused both files rather than let file order decide, and the entry was removed from this file in favour of the concern fragment's, which had probed six inflected forms against this one's two. The freed slot was deliberately not refilled -- see the cap finding below. |

## Findings that are not about this lexicon

1. **`MAX_CONCEPT_NODES` had to move, and did.** 89 base concepts + 45 here + 29 in
   `domain_entities_concern.yaml` = 163 entities in
   `data/domain/vedagraph_domain_v2/domain_registry.yaml`, against the 150 that
   `vedagraph.enrich.guards` carried when this audit began: every fragment inside its own
   budget, and the total outside the cap. Knowledge Model V2 has since raised it to 260
   with a recorded reason, so this is resolved rather than outstanding -- noted because the
   collision was structural (per-author budgets that do not add up to the shared cap) and
   will recur with the next fragment. The slot freed by VARMAN-ARMOUR was held empty until
   the cap moved and then spent on LOHA-COPPER, the one metal on the brief's target list
   that was still missing.

2. **Five aliases should be added to `SANDHI_SUPPRESSED_ALIASES`.** The substring pass runs
   on the Samaveda only, and these five clear the six-character floor while sitting inside
   a Samavedic word that means something else. They are exact and safe on the token path,
   which is where suppression leaves them. Measured hosts, in the form that dict wants:

   | alias | Samavedic host, and what it is |
   |---|---|
   | brahma (long a) | inside brahmani and brahmanah, which are aliases of VG:CONCEPT:BRAHMAN-FORMULATION -- 18 SV substring hits against 4 genuine token hits, so the priest node takes fourteen Samavedic passages from the formulation node |
   | ayasam | inside visvadhayasam and bhuridhayasam, "all-nourishing": 2 SV substring hits, 0 genuine |
   | dhanah | inside dadhanah ("holding") and yatudhanah ("sorcerers"), the second an alias of VG:CONCEPT:RAKSAS-DEMON |
   | avinam | inside kavinam, "of the poets" |
   | ayasah | inside jyayasah ("greater") and visvadhayasah |

   Until that is done, five entities in this file each carry one or two known-wrong
   Samavedic assertions. Recorded here rather than fixed by deleting the aliases: deleting
   them would give up 17 correct Rigvedic and Atharvavedic assertions to remove 23
   Samavedic ones, and the suppression list exists precisely to avoid that trade.

3. **Whitney's parenthetical IAST is an English-matching hazard.** `ENGLISH_TOKEN_PATTERN`
   is `[a-z]+(?:-[a-z]+)*`, so an accented gloss like jarayu contributes the token `jar`,
   and an unaccented one like ram contributes itself. Two candidates were retired on this
   mechanism alone. Any future English alias of three or four letters that is also a
   Sanskrit root needs checking against it.

4. **The Yajurveda is the crop corpus, and that was not the expected result.** VS 18.12-13
   lists rice, barley, beans, sesamum, kidney-beans, vetches, millet, wild rice, wheat and
   lentils, and then gold, bronze, copper, lead and tin, in two consecutive verses. Four of
   the five crop nodes and all three metal nodes here reach the Yajurveda, and a domain
   author looking for material culture should read VS 18 before anything else.

5. **The named srauta rites are not in the Samhitas as words.** agnihotra occurs once,
   rajasuya twice, vajapeya and agnistoma once each and all three of those in one verse;
   sattra, pravargya, darsapurnamasa, purusamedha and asvamedha-as-a-rite do not occur at
   all. `rituals.yaml` carries four rituals rather than the seven asked for because that is
   what the corpus supports, and its AGNIHOTRA entry is marked `confidence: LOW` with the
   fields the later system would have filled left deliberately empty.
