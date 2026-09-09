# Devatā Taxonomy V1

Overlay file: `data/domain/vedagraph_domain_v2/devata_taxonomy.yaml`
Keyed to: `data/registry/devatas.yaml` (214 entities, unmodified)
Component authority: `data/registry/devata_components.yaml` (unmodified)
Alias evidence: `scripts/probe_domain_aliases.py`, run against all four Vedas (20,210 mantras)

## What changed

Before this file, 209 of 214 `Devata` nodes carried `devata_subtype: UNKNOWN` and four
properties. There was no English label, no stem, no aliases, no epithets, no roles.

The single `devata_subtype` enum also forced a false choice — Agni had to be *either* a
deity *or* a fire *or* a ritual medium. That is replaced by two independent fields:

* **`structure`** — source-settled. What the label itself already decides, mostly by
  Sanskrit morphology. A reviewer can check every one of these without knowing any Vedic
  religion.
* **`axes`** — interpretive, and multi-valued. A deity holds several at once. Agni is now
  `FIRE_MEDIUM` *and* `PRIESTLY` *and* `TERRESTRIAL`.

`confidence` grades the axes only, never the structure.

## Coverage

| | count | share |
|---|---|---|
| Entities covered | 214 / 214 | 100% |
| `structure` assigned (not UNSPECIFIED) | 213 | 99.5% |
| `structure: UNSPECIFIED` | 1 | 0.5% |
| Real axes assigned | 110 | 51.4% |
| `axes: [UNSPECIFIED]` | 104 | 48.6% |
| `confidence: HIGH` | 139 | 65% |
| `confidence: MEDIUM` | 75 | 35% |
| `confidence: LOW` | 0 | — |

Populated relationship and display fields: 66 entries carry probed aliases, 14 carry
`composed_of`, 13 carry `member_of`, 4 carry epithets. Every entry has a non-empty
`label_en`, `label_iast`, `short_description` and `curation_note`.

The near-even split between real axes and `[UNSPECIFIED]` is the intended result, not a
shortfall. The spec is explicit that a justified UNSPECIFIED beats invented taxonomy, and
the 104 unspecified entries are overwhelmingly the long tail: one-off charm labels, patron
praise, deified war gear, named ṛṣis, and abstract theme labels. Every one of them says in
its `curation_note` *why* no axis applies, and several name the axis that was considered
and rejected.

### Structure distribution

| structure | count |
|---|---|
| INDIVIDUAL | 72 |
| ABSTRACT | 41 |
| PAIR | 38 |
| GROUP | 33 |
| HUMAN | 22 |
| PATRON_PRAISE | 7 |
| UNSPECIFIED | 1 |

### Axis distribution

Counted as assignments, not entities — an entity holds several axes.

| axis | count |
|---|---|
| UNSPECIFIED | 104 |
| WARRIOR | 20 |
| TERRESTRIAL | 18 |
| FIRE_MEDIUM | 14 |
| RITUAL_SUBSTANCE | 13 |
| ABSTRACT_PERSONIFICATION | 12 |
| ATMOSPHERIC | 12 |
| SOLAR | 11 |
| SPEECH | 11 |
| COSMIC_SOVEREIGN | 10 |
| GUARDIAN_OF_ORDER | 9 |
| DAWN_TIME | 9 |
| PRIESTLY | 8 |
| AQUATIC | 8 |
| RITUAL_OBJECT | 8 |
| HEALER | 7 |
| PSYCHOPOMP | 4 |
| ANCESTRAL | 4 |
| CHTHONIC | 3 |
| ARTISAN | 3 |

`WARRIOR` leads because Indra's axes propagate through eleven Indra-duals. No axis is
unused, which suggests the vocabulary is roughly the right size, but see the gaps named in
the judgement-call section below.

## Top 20 deities by HAS_DEVATA degree

These are the ones that matter; a reviewer should start here.

| label_en | degree | structure | axes | conf | aliases |
|---|---|---|---|---|---|
| Indra | 2869 | INDIVIDUAL | WARRIOR, COSMIC_SOVEREIGN, ATMOSPHERIC | HIGH | 7 |
| Agni | 1988 | INDIVIDUAL | FIRE_MEDIUM, PRIESTLY, TERRESTRIAL | HIGH | 5 |
| Soma Pavamāna | 1087 | INDIVIDUAL | RITUAL_SUBSTANCE | HIGH | 2 |
| the All-Gods | 805 | GROUP | UNSPECIFIED | HIGH | 0 |
| the Aśvins | 631 | PAIR | HEALER, DAWN_TIME | HIGH | 2 |
| the Maruts | 428 | GROUP | ATMOSPHERIC, WARRIOR | HIGH | 4 |
| Mitra and Varuṇa | 184 | PAIR | GUARDIAN_OF_ORDER, COSMIC_SOVEREIGN | HIGH | 3 |
| Uṣas | 182 | INDIVIDUAL | DAWN_TIME | HIGH | 7 |
| Indra and Agni | 117 | PAIR | WARRIOR, FIRE_MEDIUM | HIGH | 1 |
| the Ādityas | 100 | GROUP | COSMIC_SOVEREIGN, GUARDIAN_OF_ORDER | MEDIUM | 3 |
| Varuṇa | 99 | INDIVIDUAL | COSMIC_SOVEREIGN, GUARDIAN_OF_ORDER, AQUATIC | HIGH | 4 |
| the Ṛbhus | 96 | GROUP | ARTISAN | HIGH | 2 |
| Savitṛ | 82 | INDIVIDUAL | SOLAR, ABSTRACT_PERSONIFICATION | HIGH | 3 |
| Soma | 80 | INDIVIDUAL | RITUAL_SUBSTANCE, COSMIC_SOVEREIGN | MEDIUM | 6 |
| Pūṣan | 77 | INDIVIDUAL | TERRESTRIAL, PSYCHOPOMP, SOLAR | MEDIUM | 3 |
| Bṛhaspati | 74 | INDIVIDUAL | PRIESTLY, SPEECH, WARRIOR | HIGH | 2 |
| Indra and Varuṇa | 70 | PAIR | WARRIOR, COSMIC_SOVEREIGN, GUARDIAN_OF_ORDER | HIGH | 1 |
| Sūrya | 63 | INDIVIDUAL | SOLAR | HIGH | 4 |
| Vāyu | 53 | INDIVIDUAL | ATMOSPHERIC | HIGH | 3 |
| praise of a patron's gift | 50 | PATRON_PRAISE | UNSPECIFIED | HIGH | 0 |

### The distinctions that were required to hold

* **Sūrya vs Savitṛ** are not merged and not given identical axes. Sūrya carries `SOLAR`
  alone — the visible disc and its course. Savitṛ carries `SOLAR, ABSTRACT_PERSONIFICATION`,
  the second axis because his name is the agent noun *the Impeller* and the impelling power
  is what he is. The difference is visible in the data, not only in prose.
* **Sāvitrī Sūryā** (`VG:DEVATA:SAVITRI-SURYA`) is a third entity again: the feminine
  Sun-maiden of the wedding hymn. Her note states outright that the patronymic *sāvitrī*
  names Savitṛ as her **father** and is emphatically not an identification with him.
* **Soma vs Soma Pavamāna** differ substantively, not just by key. Pavamāna carries
  `RITUAL_SUBSTANCE` alone (the draught under the aspect of its clarification); Soma adds
  `COSMIC_SOVEREIGN` for the *soma rājan* kingship language, which belongs to the god and
  not to the straining. Their aliases are also partitioned deliberately: pavamāna forms to
  one, general soma forms to the other, so the two do not silently collect each other's
  mantras.
* **Rudra** gets Vedic axes only: `HEALER, TERRESTRIAL`. No Śiva. The note says so
  explicitly and adds that the epithet *tryambaka*, which the later tradition leans on,
  returns zero token hits in this corpus anyway.
* The same discipline is applied in three more places the brief did not ask for:
  **Yama** is denied `CHTHONIC` (in these verses his seat is the far heaven; the infernal
  Yama is post-Vedic), **Ka** is not identified with Prajāpati (that is Brāhmaṇa
  exegesis), and **Viṣṇu** is denied `COSMIC_SOVEREIGN` (Purāṇic supremacy).

---

# Judgement calls I was NOT confident about

This is the section to read first. Ordered roughly by how much a reviewer's disagreement
would cost.

### 1. The two registry files contradict each other about Mitrāvaruṇau

`data/registry/devatas.yaml` says of `VG:DEVATA:MITRAVARUNAU`: *"Named as a dual that is
deliberately not decomposed into Mitra and Varuṇa."* But
`data/registry/devata_components.yaml` carries a row for the same key with
`component_entity_ids: [VG:DEVATA:MITRAH, VG:DEVATA:VARUNAH]` and
`review_status: ACCEPTED`.

These cannot both be followed. I followed the **component file**, on the ground that it is
the reviewed authority for componenthood and its row is explicitly ACCEPTED, and I read
the `devatas.yaml` note as protecting the *entity's separateness* (which this overlay does
preserve) rather than forbidding a component edge. **This is a data defect in the registry
pair, not a judgement this overlay should be making.** One of the two files needs a human
correction. If the `devatas.yaml` note is the intended policy, then `composed_of` on that
entry must be emptied and the component row demoted.

### 2. `VG:DEVATA:INDRAVARUNAU` has no row in the component registry at all

Indra and Varuṇa are both registered entities, this is the 17th most frequent devatā in the
corpus (degree 70), and the parallel duals Indra-Agni, Indra-Vāyu, Indra-Soma,
Indra-Bṛhaspati, Indra-Brahmaṇaspati and Indra-Pūṣan all have ACCEPTED rows. Indra-Varuṇa
has none — not ACCEPTED, not NEEDS_REVIEW, not REJECTED. Its policy forbids me inferring a
decomposition from a dual ending, so I left `composed_of` empty and am reporting the gap
rather than quietly filling it. **This looks like an omission in
`devata_components.yaml`, and it is the single most likely thing in this report to be a
real bug elsewhere.**

### 3. `pṛthivī` as an alias contaminates a different entity

The probe result is genuinely awkward. Token pass: 182 clean mantras. Sandhi pass: 205 of
its hits sit inside `dyāvāpṛthivī` — the dual Heaven-and-Earth, which is a **separate
registry entity** (`VG:DEVATA:DYAVAPRTHIVYAU`). So more than half its containment hits
belong to another node.

I kept the alias, because it is Pṛthivī's own nominative and dropping it would leave the
Earth goddess unsearchable, and because this is compound-final containment (the matched
word really is `pṛthivī`) rather than the homonymy that made `ayas` a defect. But any
consumer that runs the sandhi pass will pull Dyāvāpṛthivī mantras into Pṛthivī. **If the
matcher's sandhi pass feeds anything user-visible, this alias should be removed or
suppressed per-alias.** It is recorded in the entry's `curation_note`.

### 4. `DAWN_TIME` is being used for Night, and there is no lunar axis

Two vocabulary gaps, both of which I worked around visibly rather than silently:

* **Rātrī** (Night) is given `DAWN_TIME` because it is the only division-of-the-day axis
  in the closed set, and she is regularly paired with Dawn as her counterpart. A reviewer
  who says the axis should be renamed `DIURNAL_TIME` is right, and this entry is the
  evidence for it.
* **Candramās** (the Moon), **Rākā** (full moon) and **Sinīvālī** (new moon) all get
  `[UNSPECIFIED]`. There is no lunar or celestial axis; `SOLAR` is plainly wrong and
  `ATMOSPHERIC` would put the moon in the midspace with the wind. **I would add a `LUNAR`
  axis in V2**; three entities are currently unclassifiable for want of it.

### 5. Where the RITUAL_OBJECT line falls: sacrificial implements vs war gear

I drew a hard line and applied it consistently, but it is a choice and not a fact.

`RITUAL_OBJECT` is used only for implements of the **sacrifice**: `barhiḥ`, `yūpaḥ`,
`grāvāṇaḥ`, `ulūkhalam`, `ulūkhalamusale`, `devīrdvāraḥ`, `havirdhāne śakaṭe`,
`vanaspatiḥ`.

It is **withheld** from the deified gear of the weapons hymn: `dhanuḥ` (bow), `jyā`
(bowstring), `iṣavaḥ` (arrows), `iṣudhiḥ` (quiver), `varma` (armour), `hastaghnaḥ`
(hand-guard), `ārtnī` (bow-tips), `pratodaḥ` (goad), `rathaḥ` (chariot), `rathāṅgāni`,
`rathagopāḥ`, `dundubhiḥ` (war drum) — 12 entities. Also withheld from `akṣāḥ` (gaming
dice) and `śunāsīrau` (plough and ploughshare).

A reviewer could reasonably say that anything occupying the devatā slot as a deified
implement is a `RITUAL_OBJECT`. That reading would move 13 entities out of UNSPECIFIED at
a stroke (the 12 war-gear items plus the dice; sunasirau already carries TERRESTRIAL). **If it is taken, it must be taken for all of them together**, not case by case.

### 6. Deified animals have no axis, and one exception was made

Thirteen entities are animals — `gauḥ`, `gāvaḥ`, `aśvaḥ`, `aśvāḥ`, `vājinaḥ`,
`indrasyāśvau`, `hariḥ`, `maṇḍūkāḥ`, `śyenaḥ`, `śakuntaḥ`, `śunaḥ`, `saramā`, `tārkṣyaḥ` —
and all take `[UNSPECIFIED]`, because the vocabulary has no term for them and
`RITUAL_SUBSTANCE` would describe a victim's yield rather than the creature addressed.

**I made one exception**: `sārameyau śvānau`, Yama's two dogs, get `PSYCHOPOMP`, because
the funeral verses give them an explicit office on the path of the dead. I think the
exception is earned, but it is an exception to a rule I otherwise held, and it is the
inconsistency most likely to be flagged.

### 7. `SPEECH` for `brahma`, but not for ritual utterances

`SPEECH` is reserved for deities whose domain is speech — Vāc, Sarasvatī, Bṛhaspati,
Brahmaṇaspati, Sasarparī. Bare ritual **utterances** get nothing: `svāhākṛtayaḥ`,
`hotrāśiṣaḥ`, `vivāhamantrāḥ`, `dampatyāśipaḥ`.

`VG:DEVATA:BRAHMA` (neuter *brahman*, the sacred formulation) sits exactly on that line and
I gave it `SPEECH` at MEDIUM. It is arguably an utterance and should have followed the
other four into UNSPECIFIED. **This is the one place where I knowingly applied my own rule
inconsistently**, on the ground that *brahman* is a formulated potency rather than a
recited text.

### 8. `yakṣmanāśanaḥ` was denied `HEALER`

The charm-purpose labels — `alakṣmīghnaḥ`, `duḥsvapnanāśanaḥ`, `yakṣmanāśanaḥ`,
`sapatnaghnarūpo arthaḥ`, `sapatnībādhanarūpo arthaḥ`, `garbhasmādhānarūpo arthaḥ`,
`āvartamānam manaḥ`, `subandhojīvaḥ` — all get `[UNSPECIFIED]` because the slot names the
intended act, not an agent with a domain.

`yakṣmanāśanaḥ` (the destruction of consumption) is the hardest of these to refuse, since
its whole content is the removal of disease. I refused it for consistency. Same for
`subandhojīvaḥ`, the reviving of a man. **If a reviewer wants these to be `HEALER`, the
whole charm-label group should move together.**

### 9. `Pūṣan`'s `SOLAR` axis and his Āditya membership are both weak

`TERRESTRIAL` (roads and herds) and `PSYCHOPOMP` (the funeral verses that ask him to lead
the dead) are solid. `SOLAR` is not: it rests on his membership among the Ādityas and on
the epithet *āghṛṇi*, glowing — and *āghṛṇi* returns **zero token hits** in this corpus, so
even that support is not visible in the text I can check. Marked MEDIUM.

Relatedly, `member_of: [VG:DEITYGROUP:ADITYAH]` is asserted for only four entities —
Mitra, Varuṇa, Savitṛ and Pūṣan — and all four notes mark it as uncertain, because
`devata_components.yaml` REJECTED decomposing the Ādityas on the express ground that
membership varies between passages and no source in this repo fixes the list. Pūṣan's is
the shakiest of the four.

### 10. Two DeityGroup keys were minted with nothing behind them

`VG:DEITYGROUP:ADITYAH` (4 members) and `VG:DEITYGROUP:APRIDEVATAH` (9 members, the
recurring āprī sequence of the animal offering: barhis, the divine doors, the two divine
Hotṛs, the goddess triad in both orderings, Tvaṣṭṛ, Vanaspati, the svāhā calls). The spec
invited minting these, but **no `DeityGroup` node or registry entity exists for either
key**, so both are currently dangling references. They need registry entities before
anything projects them.

### 11. Smaller calls worth a second opinion

* **`dadhikrāḥ`** — the `-āḥ` ending would mechanically give `GROUP`, but this is a variant
  label for one horse, so I used `INDIVIDUAL`. The mechanical rule misfires here.
* **`marutvānindraḥ`** — `INDIVIDUAL`, not `PAIR`, because *marutvān* is a possessive
  adjective qualifying Indra, not a dvandva. Same reason `composed_of` is empty despite
  both parties being registered.
* **`śunaḥ`** — the only `structure: UNSPECIFIED`. Ambiguous between genitive singular and
  nominative plural of *śvan*; the label does not settle number.
* **HUMAN over GROUP** — I ruled that a human collective is still human, which put
  `vasiṣṭhaputrāḥ` (sons of Vasiṣṭha) and `keśinaḥ` (the long-haired munis) in `HUMAN`
  rather than `GROUP`. Defensible either way; stated in the file header so it is at least
  a visible rule.
* **`puruṣaḥ`** — given `ABSTRACT_PERSONIFICATION, RITUAL_SUBSTANCE`. The second axis is
  unobvious: in his hymn he *is* the oblation, the victim the gods offer.
  `COSMIC_SOVEREIGN` was refused because he is the material of the world, not its ruler.
* **`agnisūyau`** — the axes depend on reading the source form as a variant of
  *agnisūryau*. That is a judgement about a possibly corrupt label, not about religion.

---

## Alias verification findings

66 entries carry aliases; every listed form was probed with
`scripts/probe_domain_aliases.py`. The top ~25 deities were spot-checked individually.
Findings worth keeping:

**Conventional stems that match nothing.** Twenty-two forms a curator would list by reflex
score **zero token hits** and were dropped: `agni`, `bṛhaspati`, `vāyu`, `aditi`, `ṛbhu`,
`ṛbhuḥ`, `indu`, `viśvedevāḥ`, `viśvedeva`, `araṇyānī`, `araṇyāni`, `śatakratu`,
`gaṇapati`, `samrāj`, `vivasvat`, `vaivasvata`, `tryambaka`, `urukrama`, `hiraṇyapāṇi`,
`āghṛṇi`, `yamī`, `indrāgni`. The corpus uses inflected forms — `agniḥ`, `agnim`, and above
all the vocative `agne` at 915 mantras.

**The registry's own label form for the Aśvins is nearly absent from the corpus.**
`aśvinau` returns **one** token hit at 83% intrusion. The corpus uses the Vedic dual
`aśvinā` (377 mantras). The Anukramaṇī label is the classical dual; the text is not.

**Viśvedevāḥ has no safe alias at all.** Both `viśvedevāḥ` and `viśvedeva` score zero,
because the corpus writes the name as two words (`viśve devāḥ`). `viśve` alone is far too
general. The fourth most frequent devatā in the corpus therefore ships with an empty
`aliases_iast`, deliberately.

**High "intrusion" is usually sandhi, not homonymy.** `indrāya` reports 20% intrusion, but
every intruding host is a word-boundary merge — `somamindrāya`, `indurindrāya`,
`bṛhadindrāya`. That is the right word with the preceding boundary erased, not a different
word, so the alias is safe. The same applies to `agnaye`, `aditiṃ`, `mitrasya`, `āditya`
and `tanūnapāt`. The genuine defect pattern (`ayas` inside `payasā`) did not appear among
the forms I kept — with the one exception of `pṛthivī` inside `dyāvāpṛthivī`, which is
judgement call 3.

**Sub-threshold aliases are protected by the matcher, not by their score.**
`MIN_SANDHI_ALIAS_CHARS = 6`, so `vāk` (3 chars, 82% containment) and `uṣo` (3 chars, 82%)
can never reach the sandhi pass; only their clean token hits (17 and 44 mantras) can match.
Both were kept for that reason, and the reason is recorded in their entries.

**Rejected on the evidence:** `agninā` (52% intrusion, 8 hits), `aśvinau` (83%, 1 hit),
`aśvibhyām` (43%, 4 hits), `vāyavaḥ` (86%, 1 hit), `apāṃ` (100 hits but it is the ordinary
genitive plural of *ap* and matches passages unrelated to Apāṃ Napāt).

## Validation

Validated by a throwaway script, not by eye. All 214 entries:

* every `entity_key` resolves against `data/registry/devatas.yaml` and appears exactly once
* all 214 registry keys are covered; entry order matches registry order
* every `structure` and every `axis` is in the allowed enum; `UNSPECIFIED` is never mixed
  with a real axis; no duplicate axes
* every `composed_of` key resolves against the registry, never self-references, and appears
  only on `PAIR`/`GROUP`
* every `composed_of` list **equals** the component list of the corresponding ACCEPTED row
  in `data/registry/devata_components.yaml` — all 14 of them — and no entry claims a
  decomposition for a row that is NEEDS_REVIEW, REJECTED or absent
* `label_en` is never empty and never contains `UNKNOWN`; `label_iast`,
  `short_description` and `curation_note` are all non-empty
* no entry exceeds 8 aliases; no duplicate aliases; every epithet has exactly `iast` + `en`
* every `member_of` value is a `VG:DEITYGROUP:*` key

Result: **0 errors, 0 warnings.**

`data/registry/devatas.yaml`, `data/registry/devata_components.yaml` and everything under
`data/semantic/` were not modified. The new file is LF-only, matching its siblings in
`data/domain/vedagraph_domain_v2/`.
