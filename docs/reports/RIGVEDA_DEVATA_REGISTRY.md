# Rigveda Devatā registry

Generated from `data/registry/devatas.yaml`
and the built knowledge layer. Entity keys are pinned identity.

**An assignment is not a textual mention.** `HAS_DEVATA: agniḥ` records that the traditional index assigns Agni as the devatā of that mantra. It does not claim that the word *agni* occurs in the Sanskrit. Literal occurrence will be a separate `MENTIONS_ENTITY` predicate produced by a later deterministic lexical phase.

## Summary

| Measure | Value |
| --- | ---: |
| Canonical entities | 214 |
| Entities with a reviewed alias | 1 |
| Composite (hyphen-joined) labels | 9 |
| Unresolved source labels | 0 |
| Entities differing only in diacritics (not merged) | 1 |

## Most frequently assigned (top 25)

| Entity key | Label | Mantras assigned | Sūktas |
| --- | --- | --- | --- |
| `VG:DEVATA:INDRAH` | indraḥ | 2,869 | 273 |
| `VG:DEVATA:AGNIH` | agniḥ | 1,988 | 223 |
| `VG:DEVATA:PAVAMANAH-SOMAH` | pavamānaḥ somaḥ | 1,087 | 113 |
| `VG:DEVATA:VISVEDEVAH` | viśvedevāḥ | 805 | 86 |
| `VG:DEVATA:ASVINAU` | aśvinau | 631 | 68 |
| `VG:DEVATA:MARUTAH` | marutaḥ | 428 | 42 |
| `VG:DEVATA:MITRAVARUNAU` | mitrāvaruṇau | 184 | 35 |
| `VG:DEVATA:USAH` | uṣāḥ | 182 | 23 |
| `VG:DEVATA:INDRAGNI` | indrāgnī | 117 | 15 |
| `VG:DEVATA:ADITYAH` | ādityāḥ | 100 | 11 |
| `VG:DEVATA:VARUNAH` | varuṇaḥ | 99 | 13 |
| `VG:DEVATA:RBHAVAH` | ṛbhavaḥ | 96 | 13 |
| `VG:DEVATA:SAVITA` | savitā | 82 | 14 |
| `VG:DEVATA:SOMAH` | somaḥ | 80 | 12 |
| `VG:DEVATA:PUSA` | pūṣā | 77 | 13 |
| `VG:DEVATA:BRHASPATIH` | bṛhaspatiḥ | 74 | 13 |
| `VG:DEVATA:INDRAVARUNAU` | indrāvaruṇau | 70 | 9 |
| `VG:DEVATA:SURYAH` | sūryaḥ | 63 | 14 |
| `VG:DEVATA:VAYUH` | vāyuḥ | 53 | 17 |
| `VG:DEVATA:DANASTUTIH` | dānastutiḥ | 50 | 15 |
| `VG:DEVATA:BRAHMANASPATIH` | brahmaṇaspatiḥ | 48 | 8 |
| `VG:DEVATA:DYAVAPRTHIVYAU` | dyāvāpṛthivyau | 47 | 11 |
| `VG:DEVATA:APAH` | āpaḥ | 45 | 6 |
| `VG:DEVATA:RUDRAH` | rudraḥ | 38 | 6 |
| `VG:DEVATA:ASHVAH` | aśvaḥ | 35 | 2 |

## Reviewed aliases

| Entity key | Alias | Type | Evidence |
| --- | --- | --- | --- |
| `VG:DEVATA:SARASVATI-ILA-BHARATI` | sarasvati-iḻā-bhāratī | SOURCE_SPELLING | Missing macron on the first component only. Both spellings name the same composite of the three ritual goddesses and are otherwise identical. |

## Suspected duplicates, deliberately not merged

These labels share an ASCII fold. A shared fold is not evidence of identity, so each keeps its own entity and a collision-breaking key. Merging one requires an alias entry with evidence.

| Shared fold | Entities |
| --- | --- |
| ASVAH | `VG:DEVATA:ASHVAAH` (aśvāḥ), `VG:DEVATA:ASHVAH` (aśvaḥ) |

## Composite labels preserved whole

The source joins several names with hyphens and states that it does not present them as a mixture of components. VedaGraph keeps the label as one entity; `HAS_COMPONENT` relations are a later, separately evidenced phase.

| Entity key | Label | Surface parts |
| --- | --- | --- |
| `VG:DEVATA:AGNIH-MARUTAH` | agniḥ-marutaḥ | agniḥ, marutaḥ |
| `VG:DEVATA:AGNIH-MITRAVARUNAU-RATRIH-SAVITA` | agniḥ-mitrāvaruṇau-rātriḥ-savitā | agniḥ, mitrāvaruṇau, rātriḥ, savitā |
| `VG:DEVATA:APTRNAH-SURYAH` | aptṛṇaḥ-sūryaḥ | aptṛṇaḥ, sūryaḥ |
| `VG:DEVATA:ILA-SARASVATI-MAHI` | iḻā-sarasvatī-mahī | iḻā, sarasvatī, mahī |
| `VG:DEVATA:INDRAH-MARUTAH` | indraḥ-marutaḥ | indraḥ, marutaḥ |
| `VG:DEVATA:INDRANI-VARUNANI-AGNAYI` | indrāṇī-varuṇānī-agnāyī | indrāṇī, varuṇānī, agnāyī |
| `VG:DEVATA:SARASVATI-ILA-BHARATI` | sarasvatī-iḻā-bhāratī | sarasvatī, iḻā, bhāratī |
| `VG:DEVATA:SARATHIH-RASMAYAH` | sārathiḥ-raśmayaḥ | sārathiḥ, raśmayaḥ |
| `VG:DEVATA:VAK-APAH` | vāk-āpaḥ | vāk, āpaḥ |

## Subtypes

5 of 214 entities carry a subtype. A subtype is only set where the source paper itself classifies the label; every other entity stays `UNKNOWN` rather than being classified by inference.

| Entity key | Label | Subtype | Evidence |
| --- | --- | --- | --- |
| `VG:DEVATA:ADITYAH` | ādityāḥ | GROUP | Named as a designated group of devatās. Classified in Akavarapu and Bhattacharya (2023), section 2.1. |
| `VG:DEVATA:DANASTUTIH` | dānastutiḥ | ABSTRACT | Praise of a patron, labelled without the patron's name; the paper calls it an abstract class rather than a deity. Classified in Akavarapu and Bhattacharya (2023), section 2.1. |
| `VG:DEVATA:INDRAGNI` | indrāgnī | PAIR | Named as a dual of Indra and Agni. Classified in Akavarapu and Bhattacharya (2023), section 2.1. |
| `VG:DEVATA:MITRAVARUNAU` | mitrāvaruṇau | PAIR | Named as a dual that is deliberately not decomposed into Mitra and Varuṇa. Classified in Akavarapu and Bhattacharya (2023), section 2.1. |
| `VG:DEVATA:VISVEDEVAH` | viśvedevāḥ | GROUP | Named as a designated group of devatās. Classified in Akavarapu and Bhattacharya (2023), section 2.1. |

## Unresolved labels

None. Every source label reaches a registered entity.

Registry entries are `review_status: UNREVIEWED`. They were derived deterministically from the source labels; a reader confirming them is the next human step, and the suspected-duplicate table above is where that review should start.
