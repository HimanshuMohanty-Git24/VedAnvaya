# Rigveda Ṛṣi registry

Generated from `data/registry/rishis.yaml`
and the built knowledge layer. Entity keys are pinned identity.

**An assignment is not a textual mention.** `HAS_DEVATA: agniḥ` records that the traditional index assigns Agni as the devatā of that mantra. It does not claim that the word *agni* occurs in the Sanskrit. Literal occurrence will be a separate `MENTIONS_ENTITY` predicate produced by a later deterministic lexical phase.

## Summary

| Measure | Value |
| --- | ---: |
| Canonical entities | 367 |
| Entities with a reviewed alias | 1 |
| Composite (hyphen-joined) labels | 1 |
| Unresolved source labels | 0 |
| Entities differing only in diacritics (not merged) | 0 |

## Most frequently assigned (top 25)

| Entity key | Label | Mantras assigned | Sūktas |
| --- | --- | --- | --- |
| `VG:RISHI:MAITRAVARUNIRVASISTHAH` | maitrāvaruṇirvasiṣṭhaḥ | 836 | 104 |
| `VG:RISHI:GAUTAMO-VAMADEVAH` | gautamo vāmadevaḥ | 558 | 55 |
| `VG:RISHI:BARHASPATYO-BHARADVAJAH` | bārhaspatyo bharadvājaḥ | 529 | 59 |
| `VG:RISHI:GATHINO-VISVAMITRAH` | gāthino viśvāmitraḥ | 501 | 49 |
| `VG:RISHI:SAUNAKO-GRTSAMADAH` | śaunako gṛtsamadaḥ | 366 | 37 |
| `VG:RISHI:AUCATHYO-DIRGHATAMAH` | aucathyo dīrghatamāḥ | 242 | 25 |
| `VG:RISHI:ANGIRASAH-KUTSAH` | āṅgirasaḥ kutsaḥ | 226 | 21 |
| `VG:RISHI:KANVO-MEDHATITHIH` | kāṇvo medhātithiḥ | 225 | 15 |
| `VG:RISHI:MAITRAVARUNIRAGASTYAH` | maitrāvaruṇiragastyaḥ | 220 | 27 |
| `VG:RISHI:RAHUGANO-GOTAMAH` | rāhūgaṇo gotamaḥ | 210 | 21 |
| `VG:RISHI:ATREYAH-SYAVASVAH` | ātreyaḥ śyāvāśvaḥ | 186 | 17 |
| `VG:RISHI:KASYAPO-ASITAH` | kāśyapo asitaḥ | 164 | 20 |
| `VG:RISHI:AUSIJO-DAIRGHATAMASAH-KAKSIVAN` | auśijo dairghatamasaḥ kakṣīvān | 151 | 11 |
| `VG:RISHI:BHAUMO-ATRIH` | bhaumo atriḥ | 127 | 15 |
| `VG:RISHI:KANVAH-SOBHARIH` | kāṇvaḥ sobhariḥ | 113 | 5 |
| `VG:RISHI:VAISVAMITRO-MADHUCCHANDAH` | vaiśvāmitro madhucchandāḥ | 112 | 11 |
| `VG:RISHI:VAIYASVO-VISVAMANAH` | vaiyaśvo viśvamanāḥ | 109 | 4 |
| `VG:RISHI:AJIGARTIH-SUNAHSEPAH` | ājīgartiḥ śunaḥśepaḥ | 107 | 8 |
| `VG:RISHI:SAKTYAH-PARASARAH` | śāktyaḥ parāśaraḥ | 105 | 10 |
| `VG:RISHI:DAIVAODASIH-PARUCCHEPAH` | daivaodāsiḥ parucchepaḥ | 100 | 13 |
| `VG:RISHI:KANVAH-PRASKANVAH` | kāṇvaḥ praskaṇvaḥ | 97 | 9 |
| `VG:RISHI:GHAURAH-KANVAH` | ghauraḥ kaṇvaḥ | 96 | 8 |
| `VG:RISHI:APTYASTRITAH` | āptyastritaḥ | 93 | 12 |
| `VG:RISHI:BARHASPATYAH-SAMYUH` | bārhaspatyaḥ śaṁyuḥ | 93 | 4 |
| `VG:RISHI:ANGIRASO-HIRANYASTUPAH` | āṅgiraso hiraṇyastūpaḥ | 91 | 7 |

## Reviewed aliases

| Entity key | Alias | Type | Evidence |
| --- | --- | --- | --- |
| `VG:RISHI:MARICAH-KASYAPAH` | mārīcāḥ kaśyapaḥ | SOURCE_SPELLING | One occurrence (RV 9.64) against five of mārīcaḥ kaśyapaḥ, including four elsewhere in Maṇḍala 9. The patronymic is written with a plural ending beside a singular personal name, which the singular form does not do. |

## Composite labels preserved whole

The source joins several names with hyphens and states that it does not present them as a mixture of components. VedaGraph keeps the label as one entity; `HAS_COMPONENT` relations are a later, separately evidenced phase.

| Entity key | Label | Surface parts |
| --- | --- | --- |
| `VG:RISHI:VARSAGIRAH-RJRASVAH-AMBARISAH-SAHADEVAH-BHAYAMANAH-SURADHASAH` | vārṣāgirāḥ ṛjrāśvaḥ-ambarīṣaḥ-sahadevaḥ-bhayamānaḥ-surādhasaḥ | vārṣāgirāḥ ṛjrāśvaḥ, ambarīṣaḥ, sahadevaḥ, bhayamānaḥ, surādhasaḥ |

## Unresolved labels

None. Every source label reaches a registered entity.

Registry entries are `review_status: UNREVIEWED`. They were derived deterministically from the source labels; a reader confirming them is the next human step, and the suspected-duplicate table above is where that review should start.
