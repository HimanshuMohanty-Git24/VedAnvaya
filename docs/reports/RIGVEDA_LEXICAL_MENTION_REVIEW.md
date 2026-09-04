# Rigveda Lexical Mention Review

Generated 2026-09-04 from `data/knowledge/rigveda_lexical_v1`.

This report reviews `MENTIONS_ENTITY`, which is **not** `HAS_DEVATA`.
A mention says the Sanskrit of the mantra contains a word whose annotated lemma
resolves to a canonical entity. It says nothing about who the mantra is addressed
to; that is traditional metadata and lives in the knowledge layer.

## Totals

| metric | value |
|---|---|
| mention assertions | 9000 |
| token occurrences | 9364 |
| mantras with at least one mention | 6560 |
| mantras with no recognised mention | 3992 |
| tokens left ambiguous (no edge created) | 711 |
| accepted lexical aliases | 40 |
| DO_NOT_MATCH suppression rules | 22 |
| match methods | {"LEMMA_ID_EXACT": 9364} |

Every mention in this build was produced by `LEMMA_ID_EXACT`: the token and the
reviewed alias share the annotation layer's own Grassmann-linked lemma identifier.
No substring, surface or fuzzy match contributed a single edge.

## Independent morphological audit

The reviewed aliases were chosen on lexical grounds. The annotation's *grammatical
gender*, which played no part in that choice, is therefore independent evidence: a
token whose gender disagrees with the deity's is a candidate false positive (a
neuter `mitrá-` is 'alliance', not Mitra).

| entity | occurrences | expected gender | observed | off-gender | rate |
|---|---|---|---|---|---|
| VG:DEVATA:INDRAH | 2435 | M | M:2435 | 0 | 0.00% |
| VG:DEVATA:AGNIH | 1724 | M | M:1724 | 0 | 0.00% |
| VG:DEVATA:SOMAH | 977 | M | M:977 | 0 | 0.00% |
| VG:DEVATA:ASVINAU | 443 | M | M:443 | 0 | 0.00% |
| VG:DEVATA:MARUTAH | 409 | M | M:409 | 0 | 0.00% |
| VG:DEVATA:VARUNAH | 396 | M | M:396 | 0 | 0.00% |
| VG:DEVATA:SURYAH | 381 | M | M:381 | 0 | 0.00% |
| VG:DEVATA:USAH | 359 | F | F:359 | 0 | 0.00% |
| VG:DEVATA:MITRAH | 325 | M | M:325 | 0 | 0.00% |
| VG:DEVATA:PRTHIVI | 320 | F | F:320 | 0 | 0.00% |
| VG:DEVATA:SAVITA | 184 | M | M:184 | 0 | 0.00% |
| VG:DEVATA:ADITIH | 173 | F | F:173 | 0 | 0.00% |
| VG:DEVATA:VAYUH | 137 | M | M:137 | 0 | 0.00% |
| VG:DEVATA:RUDRAH | 135 | M | M:135 | 0 | 0.00% |
| VG:DEVATA:BRHASPATIH | 123 | M | M:123 | 0 | 0.00% |
| VG:DEVATA:PUSA | 121 | M | M:121 | 0 | 0.00% |
| VG:DEVATA:VISNUH | 98 | M | M:98 | 0 | 0.00% |
| VG:DEVATA:INDRAGNI | 93 | M | M:93 | 0 | 0.00% |
| VG:DEVATA:MITRAVARUNAU | 92 | M | M:91, N:1 | 1 | 1.09% |
| VG:DEVATA:DYAVAPRTHIVYAU | 83 | F | F:83 | 0 | 0.00% |
| VG:DEVATA:SARASVATI | 70 | F | F:70 | 0 | 0.00% |
| VG:DEVATA:TVASTA | 65 | M | M:65 | 0 | 0.00% |
| VG:DEVATA:SACI | 55 | F | F:55 | 0 | 0.00% |
| VG:DEVATA:PARJANYAH | 27 | M | M:27 | 0 | 0.00% |
| VG:DEVATA:NIRRTIH | 24 | F | F:24 | 0 | 0.00% |
| VG:DEVATA:DRAVINODAH | 23 | M | M:23 | 0 | 0.00% |

Off-gender occurrences across all entities: **1 / 9364** (**0.01%**).
This is an upper bound on the false-positive rate for the classes it can detect;
it cannot detect an error where deity and appellative share a gender.

## Stratified sample

Sample size: **220** mention rows, chosen deterministically by sorting
on token key, so this report is stable across rebuilds and reviewable as a diff.

### High-frequency Devatās

| mantra | entity | surface | lemma | alias type | method | morphology |
|---|---|---|---|---|---|---|
| RV 1.2.5 | VG:DEVATA:INDRAH | `índraḥ` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.2.6 | VG:DEVATA:INDRAH | `índraḥ` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.3.4 | VG:DEVATA:INDRAH | `índra` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.3.5 | VG:DEVATA:INDRAH | `índra` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.3.6 | VG:DEVATA:INDRAH | `índra` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.4.4 | VG:DEVATA:INDRAH | `índram` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.4.5 | VG:DEVATA:INDRAH | `índre` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=LOC,gender=M,number=SG |
| RV 1.4.6 | VG:DEVATA:INDRAH | `índrasya` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 1.4.9 | VG:DEVATA:INDRAH | `indra` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.4.10 | VG:DEVATA:INDRAH | `índrāya` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=DAT,gender=M,number=SG |
| RV 1.1.1 | VG:DEVATA:AGNIH | `agním` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.1.2 | VG:DEVATA:AGNIH | `agníḥ` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.1.3 | VG:DEVATA:AGNIH | `agnínā` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=M,number=SG |
| RV 1.1.4 | VG:DEVATA:AGNIH | `ágne` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.1.5 | VG:DEVATA:AGNIH | `agníḥ` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.1.6 | VG:DEVATA:AGNIH | `ágne` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.1.7 | VG:DEVATA:AGNIH | `agne` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.1.9 | VG:DEVATA:AGNIH | `ágne` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.12.1 | VG:DEVATA:AGNIH | `agním` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.12.2 | VG:DEVATA:AGNIH | `agním-agnim` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.2.1 | VG:DEVATA:SOMAH | `sómāḥ` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 1.4.2 | VG:DEVATA:SOMAH | `sómasya` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 1.5.2 | VG:DEVATA:SOMAH | `sóme` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=LOC,gender=M,number=SG |
| RV 1.5.5 | VG:DEVATA:SOMAH | `sómāsaḥ` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 1.5.7 | VG:DEVATA:SOMAH | `sómāsaḥ` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 1.15.1 | VG:DEVATA:SOMAH | `sómam` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.15.5 | VG:DEVATA:SOMAH | `sómam` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.16.3 | VG:DEVATA:SOMAH | `sómasya` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 1.16.6 | VG:DEVATA:SOMAH | `sómāsaḥ` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 1.16.7 | VG:DEVATA:SOMAH | `sómam` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.3.1 | VG:DEVATA:ASVINAU | `áśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.3.2 | VG:DEVATA:ASVINAU | `áśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.15.11 | VG:DEVATA:ASVINAU | `áśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.22.1 | VG:DEVATA:ASVINAU | `aśvínau` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=DU |
| RV 1.22.2 | VG:DEVATA:ASVINAU | `aśvínā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.22.3 | VG:DEVATA:ASVINAU | `áśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.22.4 | VG:DEVATA:ASVINAU | `áśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.30.17 | VG:DEVATA:ASVINAU | `aśvinau` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.30.18 | VG:DEVATA:ASVINAU | `aśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.34.1 | VG:DEVATA:ASVINAU | `aśvinā` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.15.2 | VG:DEVATA:MARUTAH | `márutaḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=PL |
| RV 1.19.1 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.2 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.3 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.4 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.5 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.6 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.7 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.8 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.19.9 | VG:DEVATA:MARUTAH | `marúdbhiḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 1.2.7 | VG:DEVATA:VARUNAH | `váruṇam` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.17.5 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.23.4 | VG:DEVATA:VARUNAH | `váruṇam` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 1.23.6 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.24.7 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.24.8 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.24.10 | VG:DEVATA:VARUNAH | `váruṇasya` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 1.24.11 | VG:DEVATA:VARUNAH | `varuṇa` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 1.24.12 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.24.13 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |

### Rare entities (25 or fewer occurrences)

| mantra | entity | surface | lemma | alias type | method | morphology |
|---|---|---|---|---|---|---|
| RV 10.60.2 | VG:DEVATA:ASAMATIH | `ásamātim` | `ásamāti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.60.5 | VG:DEVATA:ASAMATIH | `ásamātiṣu` | `ásamāti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=LOC,gender=M,number=PL |
| RV 1.89.6 | VG:DEVATA:TARKSYAH | `tā́rkṣyaḥ` | `tā́rkṣya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.178.1 | VG:DEVATA:TARKSYAH | `tā́rkṣyam` | `tā́rkṣya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 2.32.4 | VG:DEVATA:RAKA | `rākā́m` | `rākā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 2.32.5 | VG:DEVATA:RAKA | `rāke` | `rākā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |
| RV 2.32.8 | VG:DEVATA:RAKA | `rākā́` | `rākā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 2.32.6 | VG:DEVATA:SINIVALI | `sínīvāli` | `sinīvālī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |
| RV 2.32.7 | VG:DEVATA:SINIVALI | `sinīvālyaí` | `sinīvālī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=DAT,gender=F,number=SG |
| RV 2.32.8 | VG:DEVATA:SINIVALI | `sinīvālī́` | `sinīvālī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 10.12.4 | VG:DEVATA:ASUNITIH | `ásunītim` | `ásunīti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 10.15.14 | VG:DEVATA:ASUNITIH | `ásunītim` | `ásunīti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 10.16.2 | VG:DEVATA:ASUNITIH | `ásunītim` | `ásunīti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 4.55.1 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 7.62.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 10.12.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 1.164.52 | VG:DEVATA:SARASVAN | `sárasvantam` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 7.96.4 | VG:DEVATA:SARASVAN | `sárasvantam` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 7.96.5 | VG:DEVATA:SARASVAN | `sarasvaḥ` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 4.49.1 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.2 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.3 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.2.18 | VG:DEVATA:URVASI | `urváśīḥ` | `urváśī-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=PL |
| RV 5.41.19 | VG:DEVATA:URVASI | `urváśī` | `urváśī-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 5.41.19 | VG:DEVATA:URVASI | `urváśī` | `urváśī-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 5.44.4 | VG:DEVATA:YAMI | `yamyàḥ` | `yamī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=PL |
| RV 5.47.5 | VG:DEVATA:YAMI | `yamyā̀` | `yamī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 9.68.3 | VG:DEVATA:YAMI | `yamyā̀` | `yamī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 10.146.1 | VG:DEVATA:ARANYANI | `áraṇyāni` | `araṇyāní- ~ araṇyānī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |
| RV 10.146.1 | VG:DEVATA:ARANYANI | `áraṇyāni` | `araṇyāní- ~ araṇyānī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |
| RV 10.146.2 | VG:DEVATA:ARANYANI | `araṇyāníḥ` | `araṇyāní- ~ araṇyānī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 1.122.2 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 1.186.4 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 2.3.6 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 1.62.3 | VG:DEVATA:SARAMA | `sarámā` | `sarámā-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 1.72.8 | VG:DEVATA:SARAMA | `sarámā` | `sarámā-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 3.31.6 | VG:DEVATA:SARAMA | `sarámā` | `sarámā-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 1.108.6 | VG:DEVATA:SRADDHA | `śraddhā́m` | `śraddhā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 6.26.6 | VG:DEVATA:SRADDHA | `śraddhā́bhiḥ` | `śraddhā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=F,number=PL |
| RV 7.32.14 | VG:DEVATA:SRADDHA | `śraddhā́` | `śraddhā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=F,number=SG |
| RV 1.15.7 | VG:DEVATA:DRAVINODAH | `draviṇodā́ḥ` | `draviṇodā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.15.8 | VG:DEVATA:DRAVINODAH | `draviṇodā́ḥ` | `draviṇodā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.15.9 | VG:DEVATA:DRAVINODAH | `draviṇodā́ḥ` | `draviṇodā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 1.24.9 | VG:DEVATA:NIRRTIH | `nírr̥tim` | `nírr̥ti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 1.38.6 | VG:DEVATA:NIRRTIH | `nírr̥tiḥ` | `nírr̥ti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 1.117.5 | VG:DEVATA:NIRRTIH | `nírr̥teḥ` | `nírr̥ti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=F,number=SG |

### Composite / dvandva names

These rest on a compound the annotation layer supplies as a single lexical entry.
No compound was split by this pipeline.

| mantra | entity | surface | lemma | alias type | method | morphology |
|---|---|---|---|---|---|---|
| RV 1.2.8 | VG:DEVATA:MITRAVARUNAU | `mitrāvaruṇau` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.2.9 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=M,number=DU |
| RV 1.15.6 | VG:DEVATA:MITRAVARUNAU | `mítrāvaruṇā =` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.23.5 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.35.1 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇau` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.71.9 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=M,number=DU |
| RV 1.75.5 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.111.4 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.122.6 | VG:DEVATA:MITRAVARUNAU | `mitrāvaruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.122.9 | VG:DEVATA:MITRAVARUNAU | `mitrāvaruṇau` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.21.1 | VG:DEVATA:INDRAGNI | `indrāgnī́` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.21.2 | VG:DEVATA:INDRAGNI | `indrāgnī́` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.21.3 | VG:DEVATA:INDRAGNI | `indrāgnī́` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 1.21.4 | VG:DEVATA:INDRAGNI | `indrāgnī́` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=M,number=DU |
| RV 1.21.5 | VG:DEVATA:INDRAGNI | `índrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.21.6 | VG:DEVATA:INDRAGNI | `índrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.108.1 | VG:DEVATA:INDRAGNI | `indrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.108.2 | VG:DEVATA:INDRAGNI | `indrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.108.3 | VG:DEVATA:INDRAGNI | `indrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.108.4 | VG:DEVATA:INDRAGNI | `indrāgnī` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 1.31.8 | VG:DEVATA:DYAVAPRTHIVYAU | `dyāvāpr̥thivī` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 1.35.9 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 1.52.14 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 1.61.8 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 1.101.3 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 1.112.1 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 1.115.1 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 1.115.3 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 1.159.5 | VG:DEVATA:DYAVAPRTHIVYAU | `dyāvāpr̥thivī` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 1.160.1 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | gender=F,number=DU |
| RV 1.122.2 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 1.186.4 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 2.3.6 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 2.31.5 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 4.55.3 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 5.41.7 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 7.2.6 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 10.36.1 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 10.70.6 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 10.110.6 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 4.49.1 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.2 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.3 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.4 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.49.5 | VG:DEVATA:INDRABRHASPATI | `índrābŕ̥haspátī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 4.49.6 | VG:DEVATA:INDRABRHASPATI | `indrābr̥haspatī` | `índrābŕ̥haspáti-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 4.55.1 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 7.62.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 10.12.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 10.65.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhū́mī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 10.81.3 | VG:DEVATA:DYAVABHUMI | `dyā́vābhū́mī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |

### Mandala 9

| mantra | entity | surface | lemma | alias type | method | morphology |
|---|---|---|---|---|---|---|
| RV 9.5.11 | VG:DEVATA:AGNIH | `agníḥ` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.1.1 | VG:DEVATA:SOMAH | `soma` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 9.5.11 | VG:DEVATA:VAYUH | `vāyúḥ` | `vāyú-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.1.1 | VG:DEVATA:INDRAH | `índrāya` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=DAT,gender=M,number=SG |
| RV 9.2.6 | VG:DEVATA:MITRAH | `mitráḥ` | `mitrá-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.33.3 | VG:DEVATA:VARUNAH | `váruṇāya` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=DAT,gender=M,number=SG |
| RV 9.7.8 | VG:DEVATA:MITRAVARUNAU | `mitrā́váruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 9.4.10 | VG:DEVATA:ASVINAU | `aśvínam` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 9.5.8 | VG:DEVATA:SARASVATI | `sárasvatī` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 9.10.5 | VG:DEVATA:USAH | `uṣásaḥ` | `uṣás-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=GEN,gender=F,number=SG |
| RV 9.1.6 | VG:DEVATA:SURYAH | `sū́ryasya` | `sū́rya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 9.5.9 | VG:DEVATA:TVASTA | `tváṣṭāram` | `tváṣṭar-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 9.5.11 | VG:DEVATA:BRHASPATIH | `bŕ̥haspátiḥ` | `bŕ̥haspáti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.61.9 | VG:DEVATA:PUSA | `pūṣṇé` | `pūṣán-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=DAT,gender=M,number=SG |
| RV 9.25.1 | VG:DEVATA:MARUTAH | `marúdbhyaḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=DAT,gender=M,number=PL |
| RV 9.88.3 | VG:DEVATA:DRAVINODAH | `draviṇodā́ḥ` | `draviṇodā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.67.25 | VG:DEVATA:SAVITA | `savitar` | `savitár-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=VOC,gender=M,number=SG |
| RV 9.8.8 | VG:DEVATA:PRTHIVI | `pr̥thivyā́ḥ` | `pr̥thivī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ABL,gender=F,number=SG |
| RV 9.33.3 | VG:DEVATA:VISNUH | `víṣṇave` | `víṣṇu-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=DAT,gender=M,number=SG |
| RV 9.26.1 | VG:DEVATA:ADITIH | `áditeḥ` | `áditi-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=F,number=SG |
| RV 9.73.7 | VG:DEVATA:RUDRAH | `rudrā́saḥ` | `rudrá-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 9.68.10 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 9.2.9 | VG:DEVATA:PARJANYAH | `parjányaḥ` | `parjánya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 9.113.2 | VG:DEVATA:SRADDHA | `śraddháyā` | `śraddhā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=F,number=SG |
| RV 9.68.3 | VG:DEVATA:YAMI | `yamyā̀` | `yamī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |

### Mandala 10

| mantra | entity | surface | lemma | alias type | method | morphology |
|---|---|---|---|---|---|---|
| RV 10.1.1 | VG:DEVATA:AGNIH | `agníḥ` | `agní-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.9.6 | VG:DEVATA:SOMAH | `sómaḥ` | `sóma-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.46.7 | VG:DEVATA:VAYUH | `vāyávaḥ` | `vāyú-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 10.6.5 | VG:DEVATA:INDRAH | `índram` | `índra-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.7.5 | VG:DEVATA:MITRAH | `mitrám` | `mitrá-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.8.5 | VG:DEVATA:VARUNAH | `váruṇaḥ` | `váruṇa-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.51.2 | VG:DEVATA:MITRAVARUNAU | `mitrāvaruṇā` | `mitrā́váruṇa-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=M,number=DU |
| RV 10.17.2 | VG:DEVATA:ASVINAU | `aśvínau` | `aśvín-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=M,number=DU |
| RV 10.17.7 | VG:DEVATA:SARASVATI | `sárasvatīm` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 10.1.1 | VG:DEVATA:USAH | `uṣásām` | `uṣás-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=GEN,gender=F,number=PL |
| RV 10.3.2 | VG:DEVATA:SURYAH | `sū́ryasya` | `sū́rya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=M,number=SG |
| RV 10.2.7 | VG:DEVATA:TVASTA | `tváṣṭā` | `tváṣṭar-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.13.4 | VG:DEVATA:BRHASPATIH | `bŕ̥haspátim` | `bŕ̥haspáti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.17.3 | VG:DEVATA:PUSA | `pūṣā́` | `pūṣán-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.35.13 | VG:DEVATA:MARUTAH | `marútaḥ` | `marút-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=PL |
| RV 10.2.2 | VG:DEVATA:DRAVINODAH | `draviṇodā́ḥ` | `draviṇodā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.22.14 | VG:DEVATA:SACI | `śácībhiḥ` | `śácī-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=F,number=PL |
| RV 10.65.2 | VG:DEVATA:INDRAGNI | `indrāgnī́` | `indrāgní-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=M,number=DU |
| RV 10.10.5 | VG:DEVATA:SAVITA | `savitā́` | `savitár-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.1.6 | VG:DEVATA:PRTHIVI | `pr̥thivyā́ḥ` | `pr̥thivī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=F,number=SG |
| RV 10.1.3 | VG:DEVATA:VISNUH | `víṣṇuḥ` | `víṣṇu-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.5.7 | VG:DEVATA:ADITIH | `áditeḥ` | `áditi-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=GEN,gender=F,number=SG |
| RV 10.10.11 | VG:DEVATA:NIRRTIH | `nírr̥tiḥ` | `nírr̥ti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 10.32.5 | VG:DEVATA:RUDRAH | `rudrébhiḥ` | `rudrá-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=M,number=PL |
| RV 10.1.7 | VG:DEVATA:DYAVAPRTHIVYAU | `dyā́vāpr̥thivī́` | `dyā́vāpr̥thivī́-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=ACC,gender=F,number=DU |
| RV 10.66.6 | VG:DEVATA:PARJANYAH | `parjányaḥ` | `parjánya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.108.1 | VG:DEVATA:SARAMA | `sarámā` | `sarámā-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 10.178.1 | VG:DEVATA:TARKSYAH | `tā́rkṣyam` | `tā́rkṣya-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.151.1 | VG:DEVATA:SRADDHA | `śraddháyā` | `śraddhā́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=INS,gender=F,number=SG |
| RV 10.36.1 | VG:DEVATA:USASANAKTA | `uṣā́sānáktā` | `uṣā́sānáktā-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=NOM,gender=F,number=DU |
| RV 10.66.5 | VG:DEVATA:SARASVAN | `sárasvān` | `sárasvant-` | KNOWN_LEMMA_VARIANT | LEMMA_ID_EXACT | case=NOM,gender=M,number=SG |
| RV 10.184.2 | VG:DEVATA:SINIVALI | `sinīvāli` | `sinīvālī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |
| RV 10.95.10 | VG:DEVATA:URVASI | `urváśī` | `urváśī-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=NOM,gender=F,number=SG |
| RV 10.12.4 | VG:DEVATA:DYAVABHUMI | `dyā́vābhūmī` | `dyā́vābhū́mī-` | COMPOSITE_NAME | LEMMA_ID_EXACT | case=VOC,gender=F,number=DU |
| RV 10.10.7 | VG:DEVATA:YAMI | `yamyàm` | `yamī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 10.12.4 | VG:DEVATA:ASUNITIH | `ásunītim` | `ásunīti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=F,number=SG |
| RV 10.60.2 | VG:DEVATA:ASAMATIH | `ásamātim` | `ásamāti-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=ACC,gender=M,number=SG |
| RV 10.146.1 | VG:DEVATA:ARANYANI | `áraṇyāni` | `araṇyāní- ~ araṇyānī́-` | CANONICAL_LEMMA | LEMMA_ID_EXACT | case=VOC,gender=F,number=SG |

### Mantras mentioning three or more entities

| mantra | entities |
|---|---|
| VG:RV:SAK:M01:S014:V003 | VG:DEVATA:AGNIH, VG:DEVATA:BRHASPATIH, VG:DEVATA:MITRAH, VG:DEVATA:PUSA |
| VG:RV:SAK:M01:S014:V010 | VG:DEVATA:AGNIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:VAYUH |
| VG:RV:SAK:M01:S032:V004 | VG:DEVATA:INDRAH, VG:DEVATA:SURYAH, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S033:V008 | VG:DEVATA:INDRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S035:V001 | VG:DEVATA:AGNIH, VG:DEVATA:MITRAVARUNAU, VG:DEVATA:SAVITA |
| VG:RV:SAK:M01:S035:V009 | VG:DEVATA:DYAVAPRTHIVYAU, VG:DEVATA:SAVITA, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S036:V004 | VG:DEVATA:AGNIH, VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S040:V005 | VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S043:V003 | VG:DEVATA:MITRAH, VG:DEVATA:RUDRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S044:V002 | VG:DEVATA:AGNIH, VG:DEVATA:ASVINAU, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S044:V008 | VG:DEVATA:AGNIH, VG:DEVATA:ASVINAU, VG:DEVATA:SAVITA, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S044:V014 | VG:DEVATA:ASVINAU, VG:DEVATA:MARUTAH, VG:DEVATA:SOMAH, VG:DEVATA:USAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S056:V004 | VG:DEVATA:INDRAH, VG:DEVATA:SURYAH, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S062:V003 | VG:DEVATA:BRHASPATIH, VG:DEVATA:INDRAH, VG:DEVATA:SARAMA |
| VG:RV:SAK:M01:S062:V005 | VG:DEVATA:INDRAH, VG:DEVATA:SURYAH, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S084:V001 | VG:DEVATA:INDRAH, VG:DEVATA:SOMAH, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S089:V003 | VG:DEVATA:ADITIH, VG:DEVATA:ASVINAU, VG:DEVATA:MITRAH, VG:DEVATA:SARASVATI, VG:DEVATA:SOMAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S089:V006 | VG:DEVATA:BRHASPATIH, VG:DEVATA:INDRAH, VG:DEVATA:PUSA, VG:DEVATA:TARKSYAH |
| VG:RV:SAK:M01:S090:V004 | VG:DEVATA:INDRAH, VG:DEVATA:MARUTAH, VG:DEVATA:PUSA |
| VG:RV:SAK:M01:S090:V009 | VG:DEVATA:BRHASPATIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH, VG:DEVATA:VISNUH |
| VG:RV:SAK:M01:S091:V003 | VG:DEVATA:MITRAH, VG:DEVATA:SOMAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S094:V012 | VG:DEVATA:AGNIH, VG:DEVATA:MARUTAH, VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S094:V016 | VG:DEVATA:ADITIH, VG:DEVATA:AGNIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S095:V011 | VG:DEVATA:ADITIH, VG:DEVATA:AGNIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S096:V001 | VG:DEVATA:AGNIH, VG:DEVATA:DRAVINODAH, VG:DEVATA:MITRAH |
| VG:RV:SAK:M01:S096:V009 | VG:DEVATA:ADITIH, VG:DEVATA:AGNIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S098:V003 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S100:V019 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S101:V003 | VG:DEVATA:DYAVAPRTHIVYAU, VG:DEVATA:INDRAH, VG:DEVATA:SURYAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S101:V009 | VG:DEVATA:INDRAH, VG:DEVATA:MARUTAH, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S101:V011 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S102:V011 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S103:V008 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S105:V019 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S106:V001 | VG:DEVATA:ADITIH, VG:DEVATA:AGNIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S106:V007 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S107:V002 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MARUTAH |
| VG:RV:SAK:M01:S107:V003 | VG:DEVATA:ADITIH, VG:DEVATA:AGNIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:SAVITA, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S108:V004 | VG:DEVATA:AGNIH, VG:DEVATA:INDRAGNI, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S108:V009 | VG:DEVATA:INDRAGNI, VG:DEVATA:PRTHIVI, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S108:V010 | VG:DEVATA:INDRAGNI, VG:DEVATA:PRTHIVI, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S108:V011 | VG:DEVATA:INDRAGNI, VG:DEVATA:PRTHIVI, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S108:V012 | VG:DEVATA:INDRAGNI, VG:DEVATA:SOMAH, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S108:V013 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAGNI, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S109:V004 | VG:DEVATA:ASVINAU, VG:DEVATA:INDRAGNI, VG:DEVATA:SOMAH |
| VG:RV:SAK:M01:S109:V007 | VG:DEVATA:INDRAGNI, VG:DEVATA:SACI, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S109:V008 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAGNI, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S110:V009 | VG:DEVATA:ADITIH, VG:DEVATA:INDRAH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S111:V004 | VG:DEVATA:ASVINAU, VG:DEVATA:INDRAH, VG:DEVATA:MARUTAH, VG:DEVATA:MITRAVARUNAU |
| VG:RV:SAK:M01:S111:V005 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S112:V001 | VG:DEVATA:AGNIH, VG:DEVATA:ASVINAU, VG:DEVATA:DYAVAPRTHIVYAU |
| VG:RV:SAK:M01:S112:V025 | VG:DEVATA:ADITIH, VG:DEVATA:ASVINAU, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S113:V009 | VG:DEVATA:AGNIH, VG:DEVATA:SURYAH, VG:DEVATA:USAH |
| VG:RV:SAK:M01:S113:V020 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:USAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S114:V011 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:RUDRAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S115:V001 | VG:DEVATA:AGNIH, VG:DEVATA:DYAVAPRTHIVYAU, VG:DEVATA:MITRAH, VG:DEVATA:SURYAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S115:V005 | VG:DEVATA:MITRAH, VG:DEVATA:SURYAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S115:V006 | VG:DEVATA:ADITIH, VG:DEVATA:MITRAH, VG:DEVATA:PRTHIVI, VG:DEVATA:SURYAH, VG:DEVATA:VARUNAH |
| VG:RV:SAK:M01:S117:V005 | VG:DEVATA:ASVINAU, VG:DEVATA:NIRRTIH, VG:DEVATA:SURYAH |
| VG:RV:SAK:M01:S117:V013 | VG:DEVATA:ASVINAU, VG:DEVATA:SACI, VG:DEVATA:SURYAH |

## Deliberately unresolved

711 tokens matched a registered lexical alias but produced **no edge**,
because the lemma reaches more than one entity or its alias is not reviewed as
ACCEPTED. Fail-closed is the point: these are reported, not guessed.

| status | tokens |
|---|---|
| AMBIGUOUS_LEXICAL_ENTITY | 711 |

| mantra | surface | lemma | status | candidates |
|---|---|---|---|---|
| VG:RV:SAK:M01:S008:V007 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S010:V008 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S022:V006 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V018 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V019 | `apsú` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V019 | `apsú` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V019 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V020 | `apsú` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V020 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V021 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V022 | `āpaḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S023:V023 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S024:V006 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V001 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V002 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V008 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V010 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V011 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S032:V011 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S033:V011 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S034:V002 | `venā́m` | `venā́-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:VENAH |
| VG:RV:SAK:M01:S034:V006 | `adbhyáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S035:V006 | `yamásya` | `yamá-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:YAMAH |
| VG:RV:SAK:M01:S036:V008 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S038:V005 | `yamásya` | `yamá-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:YAMAH |
| VG:RV:SAK:M01:S046:V004 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S051:V003 | `átraye` | `átri-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:ATRIH |
| VG:RV:SAK:M01:S051:V004 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S051:V011 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S052:V006 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S052:V008 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S052:V012 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S054:V010 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S055:V006 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S056:V002 | `venā́ḥ` | `vená-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:VENAH |
| VG:RV:SAK:M01:S056:V005 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S056:V006 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S057:V001 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S057:V002 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S057:V006 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S059:V003 | `apsú` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S061:V012 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S061:V014 | `venásya` | `vená-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:VENAH |
| VG:RV:SAK:M01:S063:V008 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S064:V001 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S064:V006 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S065:V004 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S065:V009 | `apsú` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S066:V008 | `yamáḥ` | `yamá-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:YAMAH |
| VG:RV:SAK:M01:S066:V008 | `yamáḥ` | `yamá-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:YAMAH |
| VG:RV:SAK:M01:S067:V010 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S070:V003 | `apā́m` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S080:V002 | `adbhyáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S080:V003 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S080:V004 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S080:V005 | `apáḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S083:V001 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S083:V002 | `ā́paḥ` | `áp-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:APAH |
| VG:RV:SAK:M01:S083:V005 | `venáḥ` | `vená-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:VENAH |
| VG:RV:SAK:M01:S083:V005 | `yamásya` | `yamá-` | AMBIGUOUS_LEXICAL_ENTITY | VG:DEVATA:YAMAH |

## Assignment is not mention

The two counts rank differently, and the difference is the result rather than a
discrepancy. `mitraḥ` is assigned to 10 mantras and mentioned in 320, because the
Anukramaṇī usually assigns the pair `mitrāvaruṇau` instead. `pavamānaḥ somaḥ` is
assigned to over a thousand mantras and mentioned in none, because the annotation
layer has no lemma for that two-word label; those mantras mention `somaḥ`.

| entity | assigned | mentioned | both | assigned only | mentioned only |
|---|---|---|---|---|---|
| indraḥ | 2869 | 2305 | 1745 | 1124 | 560 |
| agniḥ | 1988 | 1604 | 1265 | 723 | 339 |
| pavamānaḥ somaḥ | 1087 | 0 | 0 | 1087 | 0 |
| viśvedevāḥ | 805 | 0 | 0 | 805 | 0 |
| aśvinau | 631 | 439 | 350 | 281 | 89 |
| marutaḥ | 428 | 401 | 207 | 221 | 194 |
| mitrāvaruṇau | 184 | 92 | 52 | 132 | 40 |
| uṣāḥ | 182 | 353 | 127 | 55 | 226 |
| indrāgnī | 117 | 93 | 87 | 30 | 6 |
| ādityāḥ | 100 | 0 | 0 | 100 | 0 |
| varuṇaḥ | 99 | 392 | 66 | 33 | 326 |
| ṛbhavaḥ | 96 | 0 | 0 | 96 | 0 |
| savitā | 82 | 175 | 74 | 8 | 101 |
| somaḥ | 80 | 950 | 62 | 18 | 888 |
| pūṣā | 77 | 119 | 50 | 27 | 69 |

