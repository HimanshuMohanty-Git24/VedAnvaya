# Atharvaveda concern model V1 — alias audit

Author: Agent D (Atharvaveda practical-knowledge). Measured against the four canonical
corpora as loaded by `vedagraph.enrich.corpus.load_corpus`: 20,210 mantras, RV 10,552,
SV 1,844, YV 1,975, AV 5,839; 17,281 carry a translation (RV 10,500, YV 1,903, AV 4,878,
**SV 0**).

Deliverables audited here:

- `data/domain/vedagraph_domain_v2/domain_entities_concern.yaml` — 29 entities, 224
  Sanskrit aliases, 27 English aliases.
- `data/domain/vedagraph_domain_v2/concern_predicates.yaml` — the four typed edges plus an
  explicit no-edge list.

Committed by `node_type`: HUMAN_CONCERN 4, CONDITION 12, SOCIAL_RITE 4, STATE 1, PLANT 6,
OBJECT 2.

## Type vocabulary: no blocker, but a V2-only dependency

`HUMAN_CONCERN`, `CONDITION` and `SOCIAL_RITE` are **not** members of the frozen
`vedagraph.semantic.ontology.SemanticNodeType`, and they must not be: 448 sealed semantic
extractions record the ontology version they were produced under, so growing that enum
would silently redefine what `rigveda-semantic-ontology-v1` means. They are members of
`vedagraph.domain.ontology.DomainNodeType` instead, and they load through the V2 path —
`vedagraph.domain.registry.load_domain_entities`, which passes `ALL_NODE_TYPE_NAMES` as
`allowed_node_types`. A bare V1 `load_concepts(root)` still raises on them. That is the
intended behaviour, not something to route around.

This was verified end to end rather than assumed. Merging this fragment with
`data/registry/concepts.yaml` (89 entities) and the concurrently authored
`domain_entities_material.yaml` (44 entities) produces:

- **162 entities** against `MAX_CONCEPT_NODES` 260 (raised from 150 by V2);
- `duplicate_ids: []` and `alias_collisions: []` — none of the 224 Sanskrit or 27 English
  aliases here collides with the base registry **or** with the material fragment, which is
  the cross-fragment check no single-fragment audit can perform;
- all 29 entities present after load, with HUMAN_CONCERN 4, CONDITION 12, SOCIAL_RITE 4.

The four predicates in `concern_predicates.yaml` match the V2 relationship signatures in
`vedagraph.domain.ontology` exactly: `ADDRESSES_CONCERN` → `HumanConcern`, `TREATS` →
`Condition`, `PROTECTS_FROM` → `{Condition, HumanConcern}`, `USED_FOR_RITE` →
`SocialRite`.

## How the takman / yaksma collision was resolved

`VG:CONCEPT:YAKSMA-DISEASE` already claims `takman`, `takmānam` and `takmā`. Measured:
those three tokens occur in 22 of the 36 Atharvaveda mantras that carry any `takman-`
form. The unclaimed remainder is `takmane` 6, `takmann` 2, `takmanaḥ` 1, `takmanā` 1,
`takmaṃs` 1, `takmanāśana` 1, `takmanāśanam` 1, plus `rūraḥ` 1 and `rūraṃ` 1 — about 14
mantras, 39%.

Option (a) was taken: **no fever entity is added, and fever stays with
`VG:CONCEPT:YAKSMA-DISEASE`.** A sibling `TAKMAN-FEVER` built on the residual paradigm
would have carried the label "fever" over 39% of the evidence while the node labelled
"disease" kept the other 61%, so which reading a passage received would depend on which
case form the verse happened to use, and a reader of either node could not see that a
split had occurred. That is worse than one imprecise node.

The alternatives were measured and are unavailable, not merely unattractive: `hrūdu`,
`jvara` and `śītikā` have **zero** tokens anywhere in the corpus (no token in the corpus
even contains `hrūd`), `rūra` has 2 tokens against 21 substring hits at 89% intrusion
(`purūravo`, `krūram`), the English `fever` is already claimed by
`VG:CONCEPT:YAKSMA-DISEASE`, and the English `takman` has 0 hits — Whitney does not
transliterate it in this edition's translation text.

The correct fix is one edit to `data/registry/concepts.yaml`, which this fragment is
forbidden to make: move the whole `takman-` paradigm out of `YAKSMA-DISEASE` into a new
`TAKMAN-FEVER`, leaving `yakṣma-`, `amīvā-` and `rapaḥ` behind. Recorded so the decision
is a choice with a reason rather than an oversight. Consumption/`yakṣma` itself is
untouched for the same reason; the seven CONDITION entities that are genuinely kinds of
sickness are filed *under* it with `broader`.

## Per-Veda distribution

Counts are **distinct mantras**, computed by re-running the matcher's own rules over the
committed fragment: Sanskrit token equality on `TextSurfaces.tokens` everywhere, the
substring pass on `sandhi_insensitive` for the Samaveda only and only for aliases of six
folded characters or more, and `ENGLISH_TOKEN_PATTERN` over the translations. A mantra is
counted once per entity, so an entity's row does not double-count its own aliases; the
final sum does double-count a mantra that matches several entities.


| entity | node_type | RV | SV | YV | AV | total | AV share | sa-only AV | en-only AV |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `PUSTI-THRIVING` | HUMAN_CONCERN | 33 | 2 | 12 | 47 | 94 | 50% | 47 | 0 |
| `SAPATNA-RIVAL-OVERCOMING` | HUMAN_CONCERN | 6 | 1 | 7 | 87 | 101 | 86% | 87 | 0 |
| `RNA-DEBT-FREEDOM` | HUMAN_CONCERN | 12 | 0 | 1 | 12 | 25 | 48% | 9 | 8 |
| `SAMJNANA-CONCORD` | HUMAN_CONCERN | 6 | 0 | 0 | 47 | 53 | 89% | 5 | 45 |
| `KRIMI-WORMS` | CONDITION | 5 | 0 | 2 | 25 | 32 | 78% | 24 | 25 |
| `VISA-POISON` | CONDITION | 19 | 0 | 1 | 64 | 84 | 76% | 49 | 61 |
| `HARIMAN-JAUNDICE` | CONDITION | 2 | 0 | 0 | 5 | 7 | 71% | 4 | 5 |
| `KSETRIYA-HEREDITARY-DISEASE` | CONDITION | 0 | 0 | 0 | 22 | 22 | 100% | 22 | 0 |
| `BALASA-DISEASE` | CONDITION | 0 | 0 | 0 | 12 | 12 | 100% | 12 | 0 |
| `VISKANDHA-AFFLICTION` | CONDITION | 0 | 0 | 0 | 11 | 11 | 100% | 11 | 0 |
| `GRAHI-SEIZURE` | CONDITION | 1 | 0 | 0 | 14 | 15 | 93% | 14 | 0 |
| `ASRAVA-FLUX` | CONDITION | 0 | 0 | 0 | 7 | 7 | 100% | 4 | 7 |
| `KASA-COUGH` | CONDITION | 0 | 0 | 0 | 8 | 8 | 100% | 7 | 7 |
| `KRTYA-SORCERY` | CONDITION | 1 | 0 | 1 | 75 | 77 | 97% | 65 | 49 |
| `DUSVAPNYA-BAD-DREAM` | CONDITION | 0 | 1 | 0 | 21 | 22 | 95% | 21 | 0 |
| `DURNAMAN-ILL-NAMED-BEINGS` | CONDITION | 2 | 0 | 0 | 15 | 17 | 88% | 15 | 0 |
| `VIVAHA-MARRIAGE` | SOCIAL_RITE | 37 | 0 | 2 | 31 | 70 | 44% | 25 | 20 |
| `PRASUTI-CHILDBIRTH` | SOCIAL_RITE | 1 | 0 | 3 | 11 | 15 | 73% | 11 | 5 |
| `PITRYANA-FUNERARY-RITE` | SOCIAL_RITE | 1 | 0 | 0 | 9 | 10 | 90% | 9 | 0 |
| `SALA-HOUSE-BUILDING` | SOCIAL_RITE | 0 | 0 | 0 | 30 | 30 | 100% | 30 | 0 |
| `GARBHA-EMBRYO` | STATE | 92 | 12 | 21 | 61 | 186 | 33% | 59 | 43 |
| `KUSTHA-PLANT` | PLANT | 0 | 1 | 1 | 17 | 19 | 89% | 17 | 0 |
| `APAMARGA-PLANT` | PLANT | 0 | 0 | 1 | 7 | 8 | 88% | 7 | 0 |
| `ARUNDHATI-PLANT` | PLANT | 0 | 0 | 0 | 7 | 7 | 100% | 7 | 0 |
| `JANGIDA-PLANT` | PLANT | 0 | 0 | 0 | 16 | 16 | 100% | 16 | 0 |
| `DARBHA-PLANT` | PLANT | 1 | 0 | 0 | 39 | 40 | 98% | 39 | 0 |
| `GULGULU-PLANT` | PLANT | 0 | 0 | 0 | 4 | 4 | 100% | 4 | 0 |
| `MANI-AMULET` | OBJECT | 1 | 0 | 2 | 98 | 101 | 97% | 85 | 93 |
| `VARMAN-ARMOUR` | OBJECT | 24 | 3 | 6 | 36 | 69 | 52% | 35 | 2 |
| **all 29 (sum, mantras double-counted across entities)** | | 244 | 20 | 60 | 838 | 1162 | 72% | | |

Union coverage, each mantra counted once across all 29 entities:

| Veda | mantras reached | of | share |
|---|--:|--:|--:|
| RV | 238 | 10,552 | 2.3% |
| SV | 20 | 1,844 | 1.1% |
| YV | 57 | 1,975 | 2.9% |
| **AV** | **733** | **5,839** | **12.6%** |
| all | 1,048 | 20,210 | 5.2% |

### What the asymmetry shows

The Atharvaveda is 28.9% of the corpus and takes 72% of the entity-mantra pairs, and it is
reached at 12.6% against the Rigveda's 2.3% — 5.5 times the rate. The asymmetry is real and
it is the expected one: nine entities are **100% Atharvavedic** with zero matches anywhere
else (`KSETRIYA-HEREDITARY-DISEASE`, `BALASA-DISEASE`, `VISKANDHA-AFFLICTION`,
`ASRAVA-FLUX`, `KASA-COUGH`, `SALA-HOUSE-BUILDING`, `ARUNDHATI-PLANT`, `JANGIDA-PLANT`,
`GULGULU-PLANT`), and four more clear 95%: `KRTYA-SORCERY` 97%, `MANI-AMULET` 97%,
`DARBHA-PLANT` 98%, `DUSVAPNYA-BAD-DREAM` 95%.

Five entities are **not** AV-skewed, and each is worth stating rather than hiding:

- **`PUSTI-THRIVING`, 50% AV** (RV 33, YV 12). This is the genuine surprise. Thriving and
  increase read like a distinctively householder-Atharvavedic want and they are not:
  `poṣa-` and `puṣṭi-` are pan-Vedic, and the Yajurveda's `rāyaspoṣa` formula makes them a
  liturgical staple there as well. If the graph is asked "which passages concern
  prosperity" this entity will not answer "the Atharvaveda", and that is the corpus's
  answer, not a defect in the entity.
- **`GARBHA-EMBRYO`, 33% AV** (RV 92). The Rigveda uses `garbha` for the germ of fire in
  the waters and for the golden germ. Those are the same word, so they are not false
  positives, but they are why this entity is typed `STATE` and labelled "embryo" instead
  of being folded into `PRASUTI-CHILDBIRTH` as a rite. Even in the Atharvaveda the
  metaphor occurs — AV 1.33.1, "assumed Agni as embryo".
- **`VIVAHA-MARRIAGE`, 44% AV** (RV 37). Expected on textual grounds: Atharvaveda book 14
  is largely a redaction of RV 10.85, so the wedding vocabulary is shared by descent. The
  English `bride` (RV 19, AV 16) adds to the same effect.
- **`VARMAN-ARMOUR`, 52% AV** (RV 24). Armour is a warrior's object in the Rigveda and an
  amulet's metaphor in the Atharvaveda, and `varman` does not separate the two.
- **`RNA-DEBT-FREEDOM`, 48% AV** (RV 12). Debt is a shared concern; only the hymns
  *devoted* to it are Atharvavedic.

The Samaveda's 20 mantras across all 29 entities are not a finding about Samavedic content
on their own. Two causes compound: the Samaveda has **no translation**, so 27 of the 251
committed aliases cannot reach it at all, and its text is the Rigvedic praise repertoire,
which barely contains this vocabulary. Neither cause is the whole story and the number
should not be quoted without both.

## Every committed alias

`tok` is token-pass mantras, `sandhi` is substring-pass mantras (reported for every alias
regardless of eligibility, so the six-character floor can be seen working), `intr` is the
share of substring hits where the alias sits inside a longer word that does not begin with
it. High `intr` on an alias of fewer than six folded characters is informational only: that
alias is barred from the substring path, which in any case runs on the Samaveda alone.


| alias | folded (sentinels shown as `<r>`/`<m>`) | len | RV | SV | YV | AV | tok | sandhi | intr | verdict |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| **`PUSTI-THRIVING`** | | | | | | | | | | **HUMAN_CONCERN** |
| `puṣṭiṃ` | `puṣṭi<m>` | 6 | 5 | 1 | 1 | 3 | 10 | 10 | 0% | hosts are inflections |
| `puṣṭim` | `puṣṭim` | 6 | 4 | 0 | 0 | 0 | 4 | 11 | 9% | hosts are inflections |
| `puṣṭir` | `puṣṭir` | 6 | 1 | 0 | 0 | 3 | 4 | 5 | 20% | hosts read: inflections and compounds |
| `puṣṭiḥ` | `puṣṭiḥ` | 6 | 2 | 0 | 0 | 0 | 2 | 2 | 0% | hosts are inflections |
| `puṣṭyā` | `puṣṭyā` | 6 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `puṣṭyai` | `puṣṭyai` | 7 | 2 | 0 | 1 | 0 | 3 | 3 | 0% | hosts are inflections |
| `puṣṭīr` | `puṣṭīr` | 6 | 1 | 0 | 0 | 1 | 2 | 2 | 0% | hosts are inflections |
| `puṣṭaye` | `puṣṭaye` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `puṣṭikāmāya` | `puṣṭikāmāya` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `puṣṭapatir` | `puṣṭapatir` | 10 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `puṣṭapatiṃ` | `puṣṭapati<m>` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `poṣaṃ` | `poṣa<m>` | 5 | 12 | 1 | 0 | 12 | 25 | 34 | 34% | token-only; folded < 6 so barred from the sandhi path |
| `poṣam` | `poṣam` | 5 | 5 | 0 | 1 | 3 | 9 | 13 | 23% | token-only; folded < 6 so barred from the sandhi path |
| `poṣeṇa` | `poṣeṇa` | 6 | 1 | 0 | 2 | 7 | 10 | 19 | 47% | hosts read: compound-internal, same word; SV-only exposure |
| `poṣāya` | `poṣāya` | 6 | 1 | 0 | 4 | 2 | 7 | 12 | 36% | hosts read: compound-internal, same word; SV-only exposure |
| `poṣair` | `poṣair` | 6 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `poṣaiḥ` | `poṣaiḥ` | 6 | 0 | 0 | 3 | 0 | 3 | 3 | 0% | hosts are inflections |
| `poṣe` | `poṣe` | 4 | 0 | 0 | 0 | 2 | 2 | 22 | 48% | token-only; folded < 6 so barred from the sandhi path |
| `poṣā` | `poṣā` | 4 | 0 | 0 | 0 | 1 | 1 | 15 | 40% | token-only; folded < 6 so barred from the sandhi path |
| **`SAPATNA-RIVAL-OVERCOMING`** | | | | | | | | | | **HUMAN_CONCERN** |
| `sapatnān` | `sapatnān` | 8 | 1 | 0 | 2 | 41 | 44 | 53 | 0% | hosts are inflections |
| `sapatnahā` | `sapatnahā` | 9 | 1 | 1 | 3 | 16 | 21 | 26 | 0% | hosts are inflections |
| `sapatnā` | `sapatnā` | 7 | 2 | 0 | 2 | 8 | 12 | 75 | 4% | hosts are inflections |
| `sapatnīṃ` | `sapatnī<m>` | 8 | 1 | 0 | 0 | 4 | 5 | 5 | 0% | hosts are inflections |
| `sapatnānt` | `sapatnānt` | 9 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `sapatnānāṃ` | `sapatnānā<m>` | 10 | 1 | 0 | 0 | 2 | 3 | 3 | 0% | hosts are inflections |
| `sapatnānām` | `sapatnānām` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `sapatno` | `sapatno` | 7 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `sapatnāṃ` | `sapatnā<m>` | 8 | 0 | 0 | 0 | 2 | 2 | 3 | 0% | hosts are inflections |
| `sapatnās` | `sapatnās` | 8 | 0 | 0 | 0 | 2 | 2 | 3 | 0% | hosts are inflections |
| `sapatnebhyaḥ` | `sapatnebhyaḥ` | 12 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `sapatnakṣayaṇo` | `sapatnakṣayaṇo` | 14 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `sapatnakṣayaṇam` | `sapatnakṣayaṇam` | 15 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `sapatnadambhanaṃ` | `sapatnadambhana<m>` | 16 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `sapatnacātanaṃ` | `sapatnacātana<m>` | 14 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `sapatnakarśano` | `sapatnakarśano` | 14 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`RNA-DEBT-FREEDOM`** | | | | | | | | | | **HUMAN_CONCERN** |
| `ṛṇam` | `<r>ṇam` | 4 | 2 | 0 | 0 | 3 | 5 | 11 | 50% | token-only; folded < 6 so barred from the sandhi path |
| `ṛṇaṃ` | `<r>ṇa<m>` | 4 | 2 | 0 | 0 | 3 | 5 | 14 | 50% | token-only; folded < 6 so barred from the sandhi path |
| `ṛṇā` | `<r>ṇā` | 3 | 3 | 0 | 0 | 0 | 3 | 217 | 96% | token-only; folded < 6 so barred from the sandhi path |
| `ṛṇān` | `<r>ṇān` | 4 | 0 | 0 | 0 | 1 | 1 | 101 | 98% | token-only; folded < 6 so barred from the sandhi path |
| `ṛṇāni` | `<r>ṇāni` | 5 | 1 | 0 | 0 | 0 | 1 | 2 | 50% | token-only; folded < 6 so barred from the sandhi path |
| `anṛṇo` | `an<r>ṇo` | 5 | 0 | 0 | 1 | 2 | 3 | 3 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `anṛṇāḥ` | `an<r>ṇāḥ` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `anṛṇā` | `an<r>ṇā` | 5 | 0 | 0 | 0 | 1 | 1 | 17 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `debt` *(en)* | n/a | - | 4 | 0 | 1 | 7 | 12 | n/a | n/a | translation token, hosts n/a |
| `debts` *(en)* | n/a | - | 5 | 0 | 0 | 1 | 6 | n/a | n/a | translation token, hosts n/a |
| **`SAMJNANA-CONCORD`** | | | | | | | | | | **HUMAN_CONCERN** |
| `saṃjñānam` | `sa<m>jñānam` | 9 | 0 | 0 | 0 | 3 | 3 | 5 | 0% | hosts are inflections |
| `saṃjñānaṃ` | `sa<m>jñāna<m>` | 9 | 1 | 0 | 0 | 2 | 3 | 3 | 0% | hosts are inflections |
| `sāṃmanasyam` | `sā<m>manasyam` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `concord` *(en)* | n/a | - | 3 | 0 | 0 | 29 | 32 | n/a | n/a | translation token, hosts n/a |
| `harmony` *(en)* | n/a | - | 2 | 0 | 0 | 2 | 4 | n/a | n/a | translation token, hosts n/a |
| `like-minded` *(en)* | n/a | - | 0 | 0 | 0 | 14 | 14 | n/a | n/a | translation token, hosts n/a |
| **`KRIMI-WORMS`** | | | | | | | | | | **CONDITION** |
| `krimīn` | `krimīn` | 6 | 0 | 0 | 0 | 9 | 9 | 10 | 0% | hosts are inflections |
| `krimayo` | `krimayo` | 7 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `krimayaḥ` | `krimayaḥ` | 8 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `krimiṃ` | `krimi<m>` | 6 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `krimir` | `krimir` | 6 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `krimiḥ` | `krimiḥ` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `krimer` | `krimer` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `krimīṇāṃ` | `krimīṇā<m>` | 8 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `krimīṇām` | `krimīṇām` | 8 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `krimīnām` | `krimīnām` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛmiḥ` | `k<r>miḥ` | 5 | 0 | 0 | 1 | 0 | 1 | 1 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `worm` *(en)* | n/a | - | 5 | 0 | 1 | 11 | 17 | n/a | n/a | translation token, hosts n/a |
| `worms` *(en)* | n/a | - | 0 | 0 | 1 | 18 | 19 | n/a | n/a | translation token, hosts n/a |
| **`VISA-POISON`** | | | | | | | | | | **CONDITION** |
| `viṣam` | `viṣam` | 5 | 6 | 0 | 0 | 29 | 35 | 45 | 17% | token-only; folded < 6 so barred from the sandhi path |
| `viṣaṃ` | `viṣa<m>` | 5 | 3 | 0 | 0 | 17 | 20 | 31 | 36% | token-only; folded < 6 so barred from the sandhi path |
| `viṣasya` | `viṣasya` | 7 | 4 | 0 | 0 | 3 | 7 | 11 | 36% | hosts read: compound-internal, same word; SV-only exposure |
| `viṣadūṣaṇam` | `viṣadūṣaṇam` | 11 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `viṣavan` | `viṣavan` | 7 | 1 | 0 | 0 | 1 | 2 | 2 | 0% | hosts are inflections |
| `poison` *(en)* | n/a | - | 12 | 0 | 1 | 56 | 69 | n/a | n/a | translation token, hosts n/a |
| `poisons` *(en)* | n/a | - | 0 | 0 | 0 | 2 | 2 | n/a | n/a | translation token, hosts n/a |
| `poisonous` *(en)* | n/a | - | 0 | 0 | 0 | 4 | 4 | n/a | n/a | translation token, hosts n/a |
| **`HARIMAN-JAUNDICE`** | | | | | | | | | | **CONDITION** |
| `harimāṇaṃ` | `harimāṇa<m>` | 9 | 2 | 0 | 0 | 2 | 4 | 4 | 0% | hosts are inflections |
| `harimā` | `harimā` | 6 | 0 | 0 | 0 | 2 | 2 | 6 | 0% | hosts are inflections |
| `jaundice` *(en)* | n/a | - | 0 | 0 | 0 | 2 | 2 | n/a | n/a | translation token, hosts n/a |
| `yellowness` *(en)* | n/a | - | 1 | 0 | 0 | 3 | 4 | n/a | n/a | translation token, hosts n/a |
| **`KSETRIYA-HEREDITARY-DISEASE`** | | | | | | | | | | **CONDITION** |
| `kṣetriyam` | `kṣetriyam` | 9 | 0 | 0 | 0 | 6 | 6 | 6 | 0% | hosts are inflections |
| `kṣetriyaṃ` | `kṣetriya<m>` | 9 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `kṣetriyān` | `kṣetriyān` | 9 | 0 | 0 | 0 | 7 | 7 | 7 | 0% | hosts are inflections |
| `kṣetriyāt` | `kṣetriyāt` | 9 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `kṣetriyasya` | `kṣetriyasya` | 11 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `kṣetriyāṇāṃ` | `kṣetriyāṇā<m>` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṣetriyanāśany` | `kṣetriyanāśany` | 14 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| **`BALASA-DISEASE`** | | | | | | | | | | **CONDITION** |
| `balāsa` | `balāsa` | 6 | 0 | 0 | 0 | 2 | 2 | 10 | 0% | hosts are inflections |
| `balāsam` | `balāsam` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsaṃ` | `balāsa<m>` | 7 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `balāso` | `balāso` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsena` | `balāsena` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsasya` | `balāsasya` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsinaḥ` | `balāsinaḥ` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsetaḥ` | `balāsetaḥ` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `balāsanāśanīḥ` | `balāsanāśanīḥ` | 13 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`VISKANDHA-AFFLICTION`** | | | | | | | | | | **CONDITION** |
| `viṣkandhaṃ` | `viṣkandha<m>` | 10 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `viṣkandham` | `viṣkandham` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `viṣkandhād` | `viṣkandhād` | 10 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `viṣkandhāni` | `viṣkandhāni` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `viṣkandhadūṣaṇam` | `viṣkandhadūṣaṇam` | 16 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `viṣkandhadūṣaṇaṃ` | `viṣkandhadūṣaṇa<m>` | 16 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`GRAHI-SEIZURE`** | | | | | | | | | | **CONDITION** |
| `grāhir` | `grāhir` | 6 | 1 | 0 | 0 | 4 | 5 | 5 | 0% | hosts are inflections |
| `grāhiṃ` | `grāhi<m>` | 6 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `grāhyā` | `grāhyā` | 6 | 0 | 0 | 0 | 4 | 4 | 9 | 0% | hosts are inflections |
| `grāhyāḥ` | `grāhyāḥ` | 7 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `grāhyāś` | `grāhyāś` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`ASRAVA-FLUX`** | | | | | | | | | | **CONDITION** |
| `āsrāvasya` | `āsrāvasya` | 9 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `āsrāvabheṣajaṃ` | `āsrāvabheṣaja<m>` | 14 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `flux` *(en)* | n/a | - | 0 | 0 | 0 | 7 | 7 | n/a | n/a | translation token, hosts n/a |
| **`KASA-COUGH`** | | | | | | | | | | **CONDITION** |
| `kāsa` | `kāsa` | 4 | 0 | 0 | 0 | 1 | 1 | 17 | 82% | token-only; folded < 6 so barred from the sandhi path |
| `kāsam` | `kāsam` | 5 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `kāse` | `kāse` | 4 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `kāsikā` | `kāsikā` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kāsikayā` | `kāsikayā` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `cough` *(en)* | n/a | - | 0 | 0 | 0 | 7 | 7 | n/a | n/a | translation token, hosts n/a |
| **`KRTYA-SORCERY`** | | | | | | | | | | **CONDITION** |
| `kṛtyā` | `k<r>tyā` | 5 | 0 | 0 | 0 | 15 | 15 | 71 | 12% | token-only; folded < 6 so barred from the sandhi path |
| `kṛtyāṃ` | `k<r>tyā<m>` | 6 | 0 | 0 | 0 | 18 | 18 | 19 | 5% | hosts are inflections |
| `kṛtyām` | `k<r>tyām` | 6 | 0 | 0 | 0 | 2 | 2 | 5 | 20% | hosts read: inflections and compounds |
| `kṛtyāḥ` | `k<r>tyāḥ` | 6 | 0 | 0 | 0 | 6 | 6 | 6 | 0% | hosts are inflections |
| `kṛtye` | `k<r>tye` | 5 | 0 | 0 | 0 | 10 | 10 | 12 | 8% | token-only; folded < 6 so barred from the sandhi path |
| `kṛtyābhir` | `k<r>tyābhir` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyākṛtaṃ` | `k<r>tyāk<r>ta<m>` | 10 | 0 | 0 | 0 | 8 | 8 | 8 | 0% | hosts are inflections |
| `kṛtyākṛtam` | `k<r>tyāk<r>tam` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyākṛte` | `k<r>tyāk<r>te` | 9 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `kṛtyākṛto` | `k<r>tyāk<r>to` | 9 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `kṛtyākṛtā` | `k<r>tyāk<r>tā` | 9 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `kṛtyākṛtaḥ` | `k<r>tyāk<r>taḥ` | 10 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `kṛtyākṛtaś` | `k<r>tyāk<r>taś` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyākṛn` | `k<r>tyāk<r>n` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyādūṣir` | `k<r>tyādūṣir` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyādūṣaṇīś` | `k<r>tyādūṣaṇīś` | 12 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kṛtyādūṣaṇaṃ` | `k<r>tyādūṣaṇa<m>` | 12 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `witchcraft` *(en)* | n/a | - | 0 | 0 | 0 | 48 | 48 | n/a | n/a | translation token, hosts n/a |
| `sorcery` *(en)* | n/a | - | 1 | 0 | 1 | 1 | 3 | n/a | n/a | translation token, hosts n/a |
| **`DUSVAPNYA-BAD-DREAM`** | | | | | | | | | | **CONDITION** |
| `duṣvapnyaṃ` | `duṣvapnya<m>` | 10 | 0 | 0 | 0 | 14 | 14 | 15 | 6% | hosts are inflections |
| `duṣvapnyam` | `duṣvapnyam` | 10 | 0 | 0 | 0 | 1 | 1 | 2 | 50% | hosts read: compound-internal, same word; SV-only exposure |
| `duṣvapnyāt` | `duṣvapnyāt` | 10 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `duṣvapnyād` | `duṣvapnyād` | 10 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `duḥṣvapnyaṃ` | `duḥṣvapnya<m>` | 11 | 0 | 1 | 0 | 0 | 1 | 2 | 0% | hosts are inflections |
| **`DURNAMAN-ILL-NAMED-BEINGS`** | | | | | | | | | | **CONDITION** |
| `durṇāmā` | `durṇāmā` | 7 | 2 | 0 | 0 | 4 | 6 | 7 | 0% | hosts are inflections |
| `durṇāmāna` | `durṇāmāna` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `durṇāmnaḥ` | `durṇāmnaḥ` | 9 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `durṇāmnīḥ` | `durṇāmnīḥ` | 9 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `durṇāmnāṃ` | `durṇāmnā<m>` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `durṇāmnīnāṃ` | `durṇāmnīnā<m>` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `durṇāmahā` | `durṇāmahā` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `durṇāmacātanam` | `durṇāmacātanam` | 14 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `durṇāmacātanaḥ` | `durṇāmacātanaḥ` | 14 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`VIVAHA-MARRIAGE`** | | | | | | | | | | **SOCIAL_RITE** |
| `vivāhe` | `vivāhe` | 6 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `vivāhāṃ` | `vivāhā<m>` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `vadhūr` | `vadhūr` | 6 | 4 | 0 | 0 | 6 | 10 | 11 | 0% | hosts are inflections |
| `vadhūm` | `vadhūm` | 6 | 0 | 0 | 0 | 2 | 2 | 8 | 0% | hosts are inflections |
| `vadhūḥ` | `vadhūḥ` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `vadhūyur` | `vadhūyur` | 8 | 4 | 0 | 0 | 1 | 5 | 5 | 0% | hosts are inflections |
| `vadhūyor` | `vadhūyor` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `vadhūpatham` | `vadhūpatham` | 11 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `vahatuṃ` | `vahatu<m>` | 7 | 6 | 0 | 0 | 6 | 12 | 12 | 0% | hosts are inflections |
| `vahatum` | `vahatum` | 7 | 1 | 0 | 0 | 2 | 3 | 4 | 0% | hosts are inflections |
| `vahatunā` | `vahatunā` | 8 | 1 | 0 | 0 | 1 | 2 | 2 | 0% | hosts are inflections |
| `bride` *(en)* | n/a | - | 19 | 0 | 0 | 16 | 35 | n/a | n/a | translation token, hosts n/a |
| `bridegroom` *(en)* | n/a | - | 7 | 0 | 2 | 0 | 9 | n/a | n/a | translation token, hosts n/a |
| `wedding` *(en)* | n/a | - | 0 | 0 | 0 | 5 | 5 | n/a | n/a | translation token, hosts n/a |
| `marriage` *(en)* | n/a | - | 2 | 0 | 0 | 0 | 2 | n/a | n/a | translation token, hosts n/a |
| **`PRASUTI-CHILDBIRTH`** | | | | | | | | | | **SOCIAL_RITE** |
| `sūṣā` | `sūṣā` | 4 | 0 | 0 | 0 | 2 | 2 | 3 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `sūṣaṇe` | `sūṣaṇe` | 6 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jarāyu` | `jarāyu` | 6 | 0 | 0 | 0 | 5 | 5 | 12 | 7% | hosts are inflections |
| `jarāyuṇā` | `jarāyuṇā` | 8 | 1 | 0 | 3 | 2 | 6 | 7 | 12% | hosts are inflections |
| `jarāyuṇāva` | `jarāyuṇāva` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jarāyujaḥ` | `jarāyujaḥ` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jarāyubhir` | `jarāyubhir` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `garbhakaraṇaṃ` | `garbhakaraṇa<m>` | 13 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `afterbirth` *(en)* | n/a | - | 0 | 0 | 0 | 5 | 5 | n/a | n/a | translation token, hosts n/a |
| **`PITRYANA-FUNERARY-RITE`** | | | | | | | | | | **SOCIAL_RITE** |
| `pitṛyāṇaṃ` | `pit<r>yāṇa<m>` | 9 | 1 | 0 | 0 | 3 | 4 | 4 | 0% | hosts are inflections |
| `pitṛyāṇam` | `pit<r>yāṇam` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `pitṛyāṇaiḥ` | `pit<r>yāṇaiḥ` | 10 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `pitṛyāṇaś` | `pit<r>yāṇaś` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `śmaśāne` | `śmaśāne` | 7 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| **`SALA-HOUSE-BUILDING`** | | | | | | | | | | **SOCIAL_RITE** |
| `śāle` | `śāle` | 4 | 0 | 0 | 0 | 11 | 11 | 11 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `śālā` | `śālā` | 4 | 0 | 0 | 0 | 1 | 1 | 18 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `śālām` | `śālām` | 5 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `śālāṃ` | `śālā<m>` | 5 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `śālāyā` | `śālāyā` | 6 | 0 | 0 | 0 | 9 | 9 | 10 | 0% | hosts are inflections |
| `śālāyāṃ` | `śālāyā<m>` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `śālāḥ` | `śālāḥ` | 5 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `śālāpataye` | `śālāpataye` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `vāstu` | `vāstu` | 5 | 0 | 0 | 0 | 1 | 1 | 10 | 57% | token-only; folded < 6 so barred from the sandhi path |
| `vāstuṣu` | `vāstuṣu` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`GARBHA-EMBRYO`** | | | | | | | | | | **STATE** |
| `garbham` | `garbham` | 7 | 32 | 0 | 0 | 11 | 43 | 51 | 2% | hosts are inflections |
| `garbhaṃ` | `garbha<m>` | 7 | 21 | 0 | 5 | 16 | 42 | 44 | 2% | hosts are inflections |
| `garbho` | `garbho` | 6 | 19 | 0 | 9 | 15 | 43 | 47 | 7% | hosts are inflections |
| `garbhe` | `garbhe` | 6 | 9 | 1 | 3 | 5 | 18 | 19 | 0% | hosts are inflections |
| `garbha` | `garbha` | 6 | 5 | 1 | 3 | 5 | 14 | 135 | 6% | hosts are inflections |
| `garbhaḥ` | `garbhaḥ` | 7 | 4 | 0 | 0 | 1 | 5 | 10 | 50% | hosts read: compound-internal, same word; SV-only exposure |
| `garbhas` | `garbhas` | 7 | 0 | 0 | 0 | 1 | 1 | 3 | 0% | hosts are inflections |
| `garbhaś` | `garbhaś` | 7 | 1 | 0 | 0 | 1 | 2 | 3 | 0% | hosts are inflections |
| `garbhān` | `garbhān` | 7 | 0 | 0 | 0 | 3 | 3 | 5 | 0% | hosts are inflections |
| `garbhasya` | `garbhasya` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `garbhāya` | `garbhāya` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `garbhād` | `garbhād` | 7 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | hosts are inflections |
| `garbhatvam` | `garbhatvam` | 10 | 1 | 0 | 0 | 2 | 3 | 4 | 25% | hosts read: inflections and compounds |
| `embryo` *(en)* | n/a | - | 3 | 0 | 2 | 43 | 48 | n/a | n/a | translation token, hosts n/a |
| **`KUSTHA-PLANT`** | | | | | | | | | | **PLANT** |
| `kuṣṭha` | `kuṣṭha` | 6 | 0 | 0 | 0 | 3 | 3 | 13 | 0% | hosts are inflections |
| `kuṣṭhaṃ` | `kuṣṭha<m>` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `kuṣṭham` | `kuṣṭham` | 7 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `kuṣṭho` | `kuṣṭho` | 6 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `kuṣṭhas` | `kuṣṭhas` | 7 | 0 | 0 | 0 | 1 | 1 | 4 | 0% | hosts are inflections |
| `kuṣṭhā` | `kuṣṭhā` | 6 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | hosts are inflections |
| `kuṣṭhasya` | `kuṣṭhasya` | 9 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `kuṣṭhābhyām` | `kuṣṭhābhyām` | 11 | 0 | 0 | 1 | 0 | 1 | 1 | 0% | hosts are inflections |
| **`APAMARGA-PLANT`** | | | | | | | | | | **PLANT** |
| `apāmārga` | `apāmārga` | 8 | 0 | 0 | 1 | 6 | 7 | 7 | 0% | hosts are inflections |
| `apāmārgo` | `apāmārgo` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`ARUNDHATI-PLANT`** | | | | | | | | | | **PLANT** |
| `arundhati` | `arundhati` | 9 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `arundhatī` | `arundhatī` | 9 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | hosts are inflections |
| `arundhatīm` | `arundhatīm` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `arundhate` | `arundhate` | 9 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | hosts are inflections |
| **`JANGIDA-PLANT`** | | | | | | | | | | **PLANT** |
| `jaṅgiḍaḥ` | `jaṅgiḍaḥ` | 8 | 0 | 0 | 0 | 6 | 6 | 6 | 0% | hosts are inflections |
| `jaṅgiḍo` | `jaṅgiḍo` | 7 | 0 | 0 | 0 | 3 | 3 | 3 | 0% | hosts are inflections |
| `jaṅgiḍas` | `jaṅgiḍas` | 8 | 0 | 0 | 0 | 2 | 2 | 3 | 0% | hosts are inflections |
| `jaṅgiḍaṃ` | `jaṅgiḍa<m>` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jaṅgiḍaś` | `jaṅgiḍaś` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jaṅgiḍena` | `jaṅgiḍena` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jaṅgiḍasya` | `jaṅgiḍasya` | 10 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `jaṅgiḍāmatim` | `jaṅgiḍāmatim` | 12 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`DARBHA-PLANT`** | | | | | | | | | | **PLANT** |
| `darbha` | `darbha` | 6 | 0 | 0 | 0 | 23 | 23 | 29 | 0% | hosts are inflections |
| `darbhaḥ` | `darbhaḥ` | 7 | 0 | 0 | 0 | 4 | 4 | 4 | 0% | hosts are inflections |
| `darbho` | `darbho` | 6 | 0 | 0 | 0 | 6 | 6 | 6 | 0% | hosts are inflections |
| `darbhaṃ` | `darbha<m>` | 7 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `darbhā` | `darbhā` | 6 | 0 | 0 | 0 | 1 | 1 | 2 | 0% | hosts are inflections |
| `darbhena` | `darbhena` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `darbheṇa` | `darbheṇa` | 8 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `darbheṣv` | `darbheṣv` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `darbhāsaḥ` | `darbhāsaḥ` | 9 | 1 | 0 | 0 | 0 | 1 | 1 | 0% | hosts are inflections |
| **`GULGULU-PLANT`** | | | | | | | | | | **PLANT** |
| `gulgulu` | `gulgulu` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `gulgulv` | `gulgulv` | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `gulgulūḥ` | `gulgulūḥ` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `gulguloḥ` | `gulguloḥ` | 8 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| **`MANI-AMULET`** | | | | | | | | | | **OBJECT** |
| `maṇiḥ` | `maṇiḥ` | 5 | 0 | 0 | 0 | 32 | 32 | 33 | 3% | token-only; folded < 6 so barred from the sandhi path |
| `maṇiṃ` | `maṇi<m>` | 5 | 0 | 0 | 0 | 20 | 20 | 20 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `maṇir` | `maṇir` | 5 | 0 | 0 | 0 | 20 | 20 | 25 | 13% | token-only; folded < 6 so barred from the sandhi path |
| `maṇim` | `maṇim` | 5 | 0 | 0 | 0 | 14 | 14 | 14 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `maṇis` | `maṇis` | 5 | 0 | 0 | 0 | 1 | 1 | 6 | 0% | token-only; folded < 6 so barred from the sandhi path |
| `maṇinā` | `maṇinā` | 6 | 1 | 0 | 0 | 6 | 7 | 7 | 0% | hosts are inflections |
| `parṇamaṇir` | `parṇamaṇir` | 10 | 0 | 0 | 0 | 2 | 2 | 2 | 0% | hosts are inflections |
| `amulet` *(en)* | n/a | - | 0 | 0 | 2 | 93 | 95 | n/a | n/a | translation token, hosts n/a |
| `amulets` *(en)* | n/a | - | 0 | 0 | 0 | 1 | 1 | n/a | n/a | translation token, hosts n/a |
| **`VARMAN-ARMOUR`** | | | | | | | | | | **OBJECT** |
| `varma` | `varma` | 5 | 7 | 1 | 3 | 27 | 38 | 65 | 13% | token-only; folded < 6 so barred from the sandhi path |
| `varmaṇā` | `varmaṇā` | 7 | 1 | 2 | 1 | 2 | 6 | 8 | 0% | hosts are inflections |
| `varmāṇi` | `varmāṇi` | 7 | 0 | 0 | 0 | 5 | 5 | 5 | 0% | hosts are inflections |
| `varmasu` | `varmasu` | 7 | 1 | 0 | 0 | 1 | 2 | 2 | 0% | hosts are inflections |
| `varmaṇo` | `varmaṇo` | 7 | 1 | 0 | 1 | 0 | 2 | 2 | 0% | hosts are inflections |
| `varmaitad` | `varmaitad` | 9 | 0 | 0 | 0 | 1 | 1 | 1 | 0% | hosts are inflections |
| `armour` *(en)* | n/a | - | 9 | 0 | 4 | 0 | 13 | n/a | n/a | translation token, hosts n/a |
| `armor` *(en)* | n/a | - | 0 | 0 | 0 | 1 | 1 | n/a | n/a | translation token, hosts n/a |
| `mail` *(en)* | n/a | - | 11 | 0 | 2 | 1 | 14 | n/a | n/a | translation token, hosts n/a |

## Candidates dropped

This list is the other half of the deliverable. Every row was measured before it was
rejected.

### Whole entities dropped

| candidate | measurement | why dropped |
|---|---|---|
| fever / `TAKMAN-FEVER` | principal paradigm claimed by `YAKSMA-DISEASE` (22 of 36 AV mantras); `hrūdu` `jvara` `śītikā` 0 tokens; `rūra` 2 tokens / 21 substring / 89% intrusion | see the takman section above; fever left with the existing entity |
| wound / `ARUS-WOUND` | `arus` 0 tok; `aruḥ` 0 tok / 36 substring / **100%** intrusion; `arūṃṣi` 0 tok / 5 / 100% (host `parūṃṣi` "joints"); `kṣata` 0 tok / **166** substring / 100% (hosts `asṛkṣata`, `vakṣataḥ`, `rakṣatam` — aorists); English `wound` 13 but RV 9, YV 3, **AV 1** | the whole lexeme is unattested as a token; only `arusrāṇam` (2 AV) exists |
| dropsy / `JALODARA` | no token in the corpus contains `jalodar`; `udaram` 7 / `udaraṃ` 5 are "belly", a body part; English `dropsy` 0 | nothing to match |
| madness / `UNMADA` | `unmattam` 1 AV, `unmaditam` 1 AV; AV 6.111's key words sit inside the sandhi blobs `yadānunmadito` (2) and `yathānunmadito` (2), which are the **negation** ("so that he be un-mad"); English `madness` 0, `mad` 9 (RV 3, AV 6, also "mad with soma") | 2 clean mantras, and the hymn itself is unreachable |
| baldness | no Vedic token found; English `bald` 1 (SV) | nothing to match |
| barrenness | English `barren` 24 (RV 10, YV 7, AV 7) and used of land and cows; `barrenness` 1; no clean Sanskrit lexeme | no discriminating alias |
| snakebite | `ahi-` is `VG:CONCEPT:AHI-SERPENT` (ANIMAL) and English `snake` is already claimed by it; `snakes` (AV 9) left unclaimed rather than split the serpent concept | would collide with an existing entity |
| `PIPPALI-PLANT` | `pippalī` 1 AV, `pippalyaḥ` 1 AV; `pippalam`/`pippalaṃ` is the **fig** (RV 1.164.20), a different plant, so the paradigm cannot be extended; English `pippali` 0 | 2 mantras |
| `SILACI-PLANT` | `silācī` 2 AV; `silācīm` and `silāñjālā` 0 tokens | 2 mantras |
| `MUNJA-PLANT` | `muñja` 1 AV; `muñjanejanam` is Rigvedic and a different formation | 1 mantra |
| `PRSNIPARNI-PLANT` | `pṛśniparṇī` and `pṛśniparṇyā` 0 tokens anywhere | nothing to match |
| lac / `LAKSA` | `lākṣā` and `lākṣām` 0 tokens; only `lākṣe` 1 AV | 1 mantra |
| `VILOHITA` | `vilohitam` 1 AV, `vilohito` 1 AV, remaining forms Yajurvedic | 2 mantras, mixed |
| skin disease / `PAMAN` | `pāman` 0 tokens, 10 substring hits at **100%** intrusion (`upāmanthat`, `somapāmanapacyutaṃ`, `apāmanīke`, `gopāmanipadyamānamā`) | the `ayas` case exactly |
| `VISARIKA` | `viśarikā` 0 tokens | nothing to match |
| victory / `JAYA` | `jaya` 9 tok (RV 3, SV 2, YV 1, AV 3) against **283** substring at 64% intrusion; `jayam` 1, `jitim` 2, `jitiḥ` `vijayam` `saṃjayam` `abhijitim` all 0; English `victory` 58 (RV 52), `conquer` 93 (RV 61) | nominal forms unattested, English is Griffith's; overlaps `YUDH-BATTLE` and `VAJA-PRIZE` |
| safe journey / `SUGA` | `sugam` 6 (RV 5, AV 1), `sugaḥ` 2 (RV 2) | RV-skewed and thin; `ADHVAN-PATH` already claims `pathyā` |
| sorcery-as-act / `ABHICARA` | `abhicāraḥ` and `abhicāram` 0 tokens | `KRTYA-SORCERY` carries the concern |
| naming rite | no attested rite lexeme; `nāma` is far too generic to claim | no discriminating alias |

### Aliases dropped from entities that were kept

| alias | measurement | why |
|---|---|---|
| `ṛṇor` `ṛṇvati` `ṛṇvan` `ṛṇvanti` `ṛṇavo` `ṛṇadhat` `ṛṇayā` | 30+ token hits between them | **the largest trap in this batch.** All are from the root ṛ- "to set in motion" (`ṛṇoti`) or the epithet Ṛṇayā, not `ṛṇa` "debt". `RNA-DEBT-FREEDOM` would have tripled in size and been mostly wrong |
| `maṇi` (bare) | 0 tok, **144** substring, 38% intrusion — `śarmaṇi`, `dharmaṇi`, `marmaṇi`, `carmaṇi`, i.e. every `-man` stem locative | the `ayas` case; the inflected forms carry the entity instead |
| `harim` | 8 tok, **all Rigvedic** | `hari-` "the tawny one" (Soma, Indra), not `hariman` "jaundice". Same class of error as the registry's recorded `jatavedah` |
| `yātu` | 19 tok (RV 9, SV 3, AV 7) | also the 3sg imperative of the root yā- "let him come"; and `yātudhāna-` already belongs to `RAKSAS-DEMON` |
| `viṣa` (bare) | 2 tok, **286** substring, 69% intrusion (`dviṣaḥ`, `dviṣato`, `haviṣaḥ`) | four folded characters; exactly the risk flagged in the brief |
| `viṣāṇi` | 1 AV tok | `viṣāṇā`/`viṣāṇe`/`viṣāṇakā` are **horn**, a different word |
| `viṣaḥ` | 3 tok (RV 2, AV 1) | homonym risk against `viś-` forms; `JANA-PEOPLE` already holds that territory |
| `viṣaktaṃ`, `viṣat` | 1 and 4 tok | `vi-sakta` "hung up", and a verbal form |
| `sapatnī` | 4 tok, 21 substring, 29% intrusion; hosts `dāsapatnīr`, `dāsapatnīḥ`, `dāsapatnīradhūnutaṃ` ("whose lord is a Dāsa") | `dāsapatnīradhūnutaṃ` occurs in **SV 2** — the one Veda where the substring pass runs and where no translation exists to catch the error. `sapatnīṃ` (5, AV 4) carries the co-wife sense |
| `sapatnaṃ` | 1 tok, 89% intrusion, hosts `asapatnaṃ`, `indrāsapatnaṃ` | the hosts mean "**without** a rival" — the opposite claim |
| `sapatnāḥ` | 2 tok, 33% intrusion, host `asapatnāḥ` | same negation, negligible value |
| `garbhā` | 1 tok, 44% intrusion over six compound-final hosts | one mantra is not worth the substring noise |
| `vahatu` (bare) | 8 tok (RV 2, YV 3, AV 3) | homonymous with the 3sg imperative of the root vah- "let him convey". `vahatuṃ`, `vahatum`, `vahatunā` are accusative and instrumental of the noun and cannot be the imperative |
| `vahatuḥ` | 3 tok | nominative of the noun, but not separable from the verb with confidence |
| `kuṣṭhikā`, `kuṣṭhikāḥ` | 3 AV tok | `kuṣṭhikā` is a body part in the anatomical hymns, not the herb |
| `jaṅgiḍa` (bare) | 0 tok | not attested as a token; only inflected forms are |
| `puṣṭaṃ` `puṣṭam` `puṣṭe` `puṣṭāni` `puṣṭeṣu` | 26 tok | the past participle "nourished, fattened", not the noun `puṣṭi` |
| `poṣyā` `poṣaya` `poṣayiṣṇu` `poṣayiṣṇuḥ` | 6 tok | verbal forms |
| `grāhya` | 2 tok (RV 1, AV 1) | the gerundive "to be seized", a different word |
| `kravyād` and its 10 relatives | ~50 AV mantras — the largest single block dropped | means "flesh-eating". The token-pass examples show AV 5.29.8-9 `kravyād yātūnām`, flesh-eating **sorcerers**, not the cremation fire. `PITRYANA-FUNERARY-RITE` keeps `pitṛyāṇa-` and `śmaśāne` instead and pays for it in recall |
| `agnidagdha` `agnidagdhāḥ` `anagnidagdhāḥ` `pitṛmedhaḥ` `śmaśānam` `pretya` | all 0 tok | the obvious funerary nouns are simply not in this edition's tokens |
| `guggulu` `guggulum` | 0 tok; no token contains `guggul` | the corpus spells it `gulgulu`; committed under the attested spelling |
| `āsrāva` `āsrāvam` `āsrāvāḥ` `atisāraḥ` | 0 tok | only `āsrāvasya` and `āsrāvabheṣajaṃ` tokenise; see the residuals |
| `varman` `varmaṇaḥ` `maṇayaḥ` `parṇamaṇiḥ` `kṛmi` `kṛmim` `kṛmiṃ` `kṛmayaḥ` `kṛmīn` `kṛmeḥ` `kṛmīṇām` | 0 tok each | guessed inflections the corpus does not print. `kṛmi-` is the decisive case: the Atharvaveda spells it **`krimi-`**, and the guessed `kṛmi-` paradigm returned 0 AV hits while the attested `krimi-` paradigm returns 33 |
| `maṇigrīvam` | 1 RV tok | a horse's neck-jewel |
| `aśmavarma` | 7 AV tok | a distinct compound, "stone-armour"; left unclaimed rather than absorbed |
| `kṛtyaiṣā` `kṛtyāsaktir` `grāhyāmitrāṃs` `grāhyainaṃ` `garbhadhim` `garbharasā` | 1-2 tok each | sandhi blobs, or different compounds |

### English aliases dropped

Whitney and Lanman's diction was measured, not assumed from Griffith. The translations
print the Sanskrit in parentheses, which made several of these decisive.

| alias | hits | why |
|---|---|---|
| `spell` / `spells` | 28 (AV 26) / 7 | Whitney's rendering of **vacas** "speech": AV 1.29.5 "up this spell (vácas) of mine". Would have filed speech passages under witchcraft. 26 AV mantras given up on purpose |
| `sorcerer` | 18 (AV 17) | renders **yatudhana** (AV 1.7.1), which is `RAKSAS-DEMON`'s territory: it names the agent, not the affliction |
| `seizure` | 19 (AV 19) | renders **haras**, "the grasp of the gods" (AV 2.2.2), **not** grāhi. `GRAHI-SEIZURE` is left Sanskrit-only |
| `womb` | 56 (YV 18, AV 29) | renders **yoni** (AV 3.5.8), not garbha |
| `increase` | 128 (RV 65) | Griffith's verb, "increase our wealth" |
| `fatness` | 91 (RV 56) | Griffith-specific and Rigveda-weighted |
| `prosper` / `thrive` / `growth` | 106 (RV 64) / 15 / 27 | verbs. `PUSTI-THRIVING` is committed with **no** English alias as a result |
| `charm` / `charms` | 10 / 9 | spread RV 5, YV 2, AV 3; both translators use it loosely |
| `shed` | 63 (RV 54) | the verb, "shed light". Not a hut |
| `dream` / `dreams` | 12 (RV 8, AV 3) / 2 | Rigveda-weighted and generic. `DUSVAPNYA-BAD-DREAM` claims the **evil** dream, and `duṣvapnya-` says so where "dream" does not |
| `burnt` / `funeral` / `cremated` | 18 / 3 / 2 | generic or too thin; `PITRYANA-FUNERARY-RITE` is Sanskrit-only |
| `hall` | 5 (RV 4, YV 1, **AV 0**) | Griffith's, and absent from the Atharvaveda |
| `mad` / `crazed` | 9 / 1 | "mad with soma" |
| `rival`, `rivals` | — | already claimed by `VG:CONCEPT:SATRU-ENEMY`; `SAPATNA-RIVAL-OVERCOMING` is Sanskrit-only |
| `fever` | — | already claimed by `VG:CONCEPT:YAKSMA-DISEASE` |
| `snake` | — | already claimed by `VG:CONCEPT:AHI-SERPENT` |
| zero hits, unusable | 0 | `enchantment`, `bewitchment`, `co-wife`, `co-wives`, `debtless`, `unanimity`, `foetus`, `fetus`, `cremation`, `burial`, `hut`, `pyre`, `corpse`, `grave`, `cremate`, `childbirth`, `parturition`, `delivery`, `witch`, `witches`, `roundworm`, `worm-killing`, `house-building`, `kshetriya`, `hereditary`, `grahi`, `madness`, `vishkandha`, `balasa`, `takman`, `plaster`, `dropsy`, `gripe` |
| plant transliterations | 0 | `kushtha`, `apamarga`, `arundhati`, `jangida`, `pippali`, `guggulu`, `munja`, `silachi` all return **zero**, and `darbha` returns 1 (Rigvedic). **Whitney transliterates no plant name in this edition's translation text**, so all six PLANT entities are necessarily Sanskrit-only. This is a property of the translation, not of the herbs |

## Interpretive limits of TREATS and PROTECTS_FROM

A passage naming a condition is not a passage prescribing a treatment for it. The matcher
reports that a folded alias equals a token of the stored text; that is a fact about the
wording and nothing else. Three rules were applied.

**`TREATS` is never asserted from a bare lexical match on the ailment's own name.** Seven
of the twelve CONDITION entities are in `treats`, and each earned it on evidence outside
the bare name:

- an explicit remedy-or-destroyer compound printed in the corpus itself and committed as
  an alias — `kṣetriyanāśany` "destroying kṣetriya" (4 AV), `balāsanāśanīḥ` (1),
  `viṣkandhadūṣaṇam` + `viṣkandhadūṣaṇaṃ` (3), `āsrāvabheṣajaṃ` (1). This is the text
  saying "this passage is a treatment for X", not an inference from co-occurrence;
- or a match set small enough to have been read to the end. `HARIMAN-JAUNDICE` qualifies
  this way: 4 matches in the entire corpus — AV 1.22.4, AV 9.8.9, RV 1.50.11, RV 1.50.12 —
  and all four are the yellowness-transfer charm, including both Rigvedic ones;
- or a distribution that exists only inside the charms. `KRIMI-WORMS` (100% AV on the
  Sanskrit path) and `KASA-COUGH` (100% AV) qualify: no Rigvedic or Yajurvedic descriptive
  use exists to dilute them.

**Where both predicates could be argued, the weaker was chosen.** `VISA-POISON` is the
clearest case: 64 of its 84 matches are Atharvavedic and many are the poison charms of
AV 4.6-7, but 20 are Rigvedic or Yajurvedic and were not read one at a time, so it takes
`PROTECTS_FROM`. That predicate is true of the charm passages and is not *false* of the
descriptive ones in the way `TREATS` would be. `KRTYA-SORCERY` is kept out of `treats` on
the same principle even though its counter-witchcraft hymns are as therapeutic in intent
as any remedy: what those hymns do to a spell is turn it back on its maker, not cure it.
`GRAHI-SEIZURE` likewise — the corpus asks release from Grāhi's fetters, which is
apotropaic rather than medical.

**An entity in no predicate list is a decision, not a gap.** The six PLANT entities,
`GARBHA-EMBRYO`, `MANI-AMULET` and `VARMAN-ARMOUR` get no typed edge and are listed in
`no_typed_edge` so the omission is visible. A passage matching `KUSTHA-PLANT` tells you the
herb is named there; the ailment it is named against is a separate entity that the same
passage matches separately. Joining herb to ailment inside one passage would be an
inference about which of two co-mentioned entities acts on the other, and nothing in the
stored text licenses it. That edge belongs to a reviewed extraction. `MANI-AMULET` in
particular is neither a Condition nor `used_for_rite`: an amulet hymn is about the amulet.

Expect the projected shape to be one typed edge plus two or three plain mentions on a
dense charm. `MAX_CONCEPTS_PER_PASSAGE` is 4, so the weakest matches on the densest
passages will be dropped; the enrichment run counts and reports that, so it is not silent.

## Known residuals, measured and left in place

- `grāhyā` and `grāhyāḥ` are spelled identically to the feminine of the gerundive
  `grāhya` "to be seized". All seven token-pass matches were read — AV 2.9.1, 2.10.8,
  6.112.1, 6.112.2, 12.2.39, 16.5.1, 19.45.5 — and all are Grāhi the disease-power
  ("release him from the fetters of Grāhi"). AV 12.2.39 `grāhyā gṛhāḥ` is the one where a
  gerundive reading is arguable. `grāhya` itself is excluded.
- `viṣasya` has 36% intrusion with host `taviṣasya` "of the strong". The exposure is
  Samaveda-only and `taviṣasya` has SV 0, so it is kept.
- `garbhaḥ` has 50% intrusion with host `hiraṇyagarbhaḥ`, the cosmogonic epithet. Kept:
  the host is `garbha` in a compound, so it is the same word, and this is precisely the
  metaphor the entity's label and definition already declare.
- `poṣeṇa` 47% and `poṣāya` 36%, hosts `rāyaspoṣeṇa` and `rāyaspoṣāya` "with/for increase
  of wealth". Kept: same word, right sense, compound-final.
- `kṛtyām` 20%, host `ākṛtyāmūn` (`ā-kṛtya`, "having made"), one occurrence, SV 0. Kept.
- `ASRAVA-FLUX` recall is low and known: the nominative and accusative of `āsrāva` are
  never tokenised in this edition — they appear only inside `cāsrāvaṃ` and `anāsrāvam` —
  so the entity reaches 7 mantras where the Atharvaveda's flux material is roughly twice
  that. It is committed because the 7 are exact, not because the coverage is good.
- `PITRYANA-FUNERARY-RITE` reaches 10 mantras. Atharvaveda book 18 is the funeral book and
  most of it carries no funerary noun that tokenises cleanly in this edition; `kravyād`
  would have raised recall to about 50 and was rejected above.
- `PUSTI-THRIVING`, `SAPATNA-RIVAL-OVERCOMING`, `KSETRIYA-HEREDITARY-DISEASE`,
  `BALASA-DISEASE`, `VISKANDHA-AFFLICTION`, `GRAHI-SEIZURE`, `DUSVAPNYA-BAD-DREAM`,
  `DURNAMAN-ILL-NAMED-BEINGS`, `SALA-HOUSE-BUILDING`, `PITRYANA-FUNERARY-RITE` and all six
  PLANT entities carry **no English alias**. They are unverifiable against the translation
  by construction, and in the Samaveda they are unverifiable at all.

## Reproducing this

```
PYTHONIOENCODING=utf-8 python scripts/probe_domain_aliases.py --file <aliases> --collisions
```

The committed set was probed in one batch: 228 Sanskrit aliases and 46 English candidates.
The fragment was then merged and loaded through the real V2 path in an isolated copy of
`data/`, so the merge was proved rather than predicted, and the live
`domain_registry.yaml` build artifact was left untouched for the concurrent V2 process.
Collisions against `data/registry/concepts.yaml`: **none** on either side. Zero-match
aliases in the committed set: **none**. A throwaway assertion script checked, without
eyeballing, that every `concept_id` matches `CONCEPT_ID_PATTERN`, every `broader` and every
`related_devatas` key resolves against `data/registry/concepts.yaml` and
`data/registry/devatas.yaml`, every English alias matches `ENGLISH_ALIAS_PATTERN`, no alias
is claimed twice within the fragment or against the existing registry or against
`ambiguous_aliases`, each entity appears in exactly one predicate list, and every predicate
list references only entities of the `node_type` it accepts.

One method note, because it changed the outcome more than any other decision: guessing
inflected forms and probing them found nothing for `krimi-`, `duṣvapnya-` and `kāsa-`,
because the Atharvaveda's spellings are `krimi-` (not `kṛmi-`), `duṣvapnya-` (not
`duḥṣvapnya-`) and the paradigms run through `krimer` and `krimayo`. Dumping the corpus's
own 64,773-token folded vocabulary and reading the attested forms out of it recovered 33,
21 and 8 Atharvavedic mantras that guessed paradigms had scored as zero. Enumerate the
corpus's forms; do not probe the forms you expect.

