# Mapping the Rigvedic verbal roots onto the action-predicate vocabulary

**Artefact**: `data/registry/action_root_map.yaml` (`vedagraph-action-root-map-v1`)
**Vocabulary**: `data/registry/action_predicates.yaml` (`vedagraph-action-predicates-v1`, closed, unmodified)
**Adjudicator**: `MODEL_ADJUDICATED` / `claude-opus-5`
**Knowledge model**: V3, agentive layer

---

## 1. What was mapped, and against what

The roots come from the University of Zurich manual morphosyntactic annotation of Lubotsky's Rigveda,
carried in `data/knowledge/rigveda_lexical_v1/tokens.jsonl`. Streaming that file for
`part_of_speech == "root"` yields **32,029 tokens over 702 distinct lemma labels**.

The supplied inventory said 662. That gap is the first finding of this exercise and it is not a
rounding difference; see §2.

Every one of the **437 lemmas with 5 or more tokens** was adjudicated individually — either onto a
predicate or onto `UNMAPPED_ROOT` with a stated reason. Seven roots below the floor were rescued (21
tokens) and are counted as mapped. The remaining 258 sub-floor lemmas (488 tokens, 1.52% of the
corpus) fall under a stated bulk rule and are not listed individually.

| | roots | tokens | share |
|---|---|---|---|
| mapped to a predicate | **342** | **29,665** | **92.62%** |
| `UNMAPPED_ROOT`, adjudicated individually | 102 | 1,876 | 5.86% |
| `UNMAPPED_ROOT`, below the frequency floor | 258 | 488 | 1.52% |
| total | 702 | 32,029 | 100% |

**Achieved token coverage: 0.9262.**

Every predicate in the vocabulary received at least one root. That was not a given — see §7.

### Method

For each root I asked what it means *as a verb in Rigvedic usage*, using the annotation's own
inflected surfaces as the primary evidence and Grassmann's sense divisions (which this annotation
was corrected against) as the frame. Where a decision was contestable I read verses. **75 roots were
checked against real Rigvedic verses** — the top 15 by frequency, every root I found hard, and every
root whose mapping the report below defends. Their `verses_read` and `examples` fields carry the
citations, and the notes quote Griffith directly.

Griffith's English is evidence about a nineteenth-century translator's word choice, not about the
Sanskrit. It was used only to confirm a verb *class* — that `pāhi` in RV 1.2.1 is about drinking and
in RV 1.143.8 about guarding — never to settle a sense the Sanskrit did not already support.

Two decisions were settled by **measurement** rather than by reading, because reading alone kept
producing a tie. Streaming the annotation to collect the case inventory of the pada containing each
root token gives a corpus-wide baseline of **DAT 12.2%, LOC 11.1%** over all 32,029 root tokens.
Against that baseline:

| root | DAT | LOC | reading |
|---|---|---|---|
| `√maṃh-` | 72.3% | 6.4% | unambiguous GRANTS |
| `√rā- 1` | 48.6% | 5.5% | unambiguous GRANTS |
| `√dā- 1` | 38.4% | 6.5% | unambiguous GRANTS |
| `√yam-` | 36.2% | 8.4% | GRANTS, on the same profile |
| **`√dhā- 1`** | **19.3%** | **30.6%** | **the mirror profile — placement, not giving** |
| `√kr̥-` | 22.6% | 9.9% | baseline-ish LOC |
| `√bhr̥-` | 27.0% | 9.6% | baseline-ish LOC |
| `√juṣ-` | 4.7% | 3.4% | two-place, neither role |

---

## 2. The key hazard: `root_folded` cannot carry this map

**`root_folded` must not be the join key, and the supplied inventory is built on it.**

`root_folded` is `fold_alias(normalized_lemma)`. The fold casefolds, strips Vedic tone marks, and —
critically — **drops the scholarly sense number**. Recomputing it over the annotation reproduces the
supplied inventory exactly: 662 keys, zero token mismatches. Which means 702 lemmas were silently
compressed into 662 keys. **37 folded keys carry two or three distinct roots each**, including every
case the brief flagged:

| folded key | collapses | tokens |
|---|---|---|
| `pā` | `√pā- 2` drink / `√pā- 1` protect | 405 / 261 |
| `vid` | `√vid- 2` know / `√vid- 1` find | 391 / 211 |
| `as` | `√as- 1` be / `√as- 2` throw | 1366 / 32 |
| `yā` | `√yā- 1` go / `√yā- 2` implore | 572 / 150 |
| `v`+sentinel | `√vr̥- 1` cover / `√vr̥- 2` choose | 179 / 147 |
| `iṣ` | `√iṣ- 2` desire / `√iṣ- 1` impel | 77 / 73 |
| `pat` | `√pat- 1` fly / `√pat- 2` rule | 94 / 30 |
| `vas` | `√vas- 2` clothe / `√vas- 1` dawn / `√vas- 3` dwell | 89 / 85 / 9 |
| … 29 more | | |

The supplied inventory's single `pā` row is **666 tokens labelled `√pā- 2`**, with `piba` and `pāhi`
sitting side by side in its own `example_surfaces`. Consuming it as given would have filed all Soma
drinking and all divine protection under one predicate. The same row structure would have merged
"Indra *is*" with "Indra *shoots*", and "we *know*" with "he *found* the cows".

The map is therefore keyed on **`lemma_label`** (unique) with **`lemma_id`** (the VedaWeb identifier,
e.g. `lemma_pA_5404` vs `lemma_pA_5405`) as the machine join key. `root_folded` is retained per entry
only so a consumer of the older inventory can see which row an entry belongs to.

A second, smaller hazard: the fold replaces vocalic `r̥`/`r̥̄`, the lateral series and the anusvara with
**private-use sentinels**. 82 of the 444 entries have an invisible U+E000-range character in their
`root_folded`, and **`√r̥-` (146 tokens) folds to a bare U+E000 with no letter at all**. I initially
recorded that as "the empty string", because that is what it prints as; the correction is in the
artefact. Every `root_folded` in the file is emitted as a double-quoted YAML scalar with `\uXXXX`
escapes so the sentinels survive a round trip and stay visible.

---

## 3. The `pā- 1` / `pā- 2` resolution

**`√pā- 1` = PROTECT. `√pā- 2` = DRINK.** The verse that settles it, and the reason it needed
settling:

> **RV 1.2.1** — `vāyav ā yāhi darśateme somā araṁkr̥tāḥ | teṣām **pāhi** śrudhī havam`
> "BEAUTIFUL Vayu, come, for thee these Soma drops have been prepared: **Drink of them**, hearken to
> our call." → `√pā- 2`

> **RV 1.143.8** — `... śivebhir naḥ pāyubhiḥ **pāhi** śagmaiḥ | ... pari **pāhi** no jāḥ`
> "**Keep us** incessantly with guards that cease not, Agni... O Helper, **keep** our children."
> → `√pā- 1`

**The same surface form, `pāhi`, appears in both roots' token sets.** No amount of string work can
separate them; only the annotation's `lemma_id` can. Corroborating each side:

- `√pā- 2` (405 tokens): `piba`, `pibatam`, `papivān`, `pītvā`, `pātave`, `apām`. RV 2.11.10
  `papivān sutasya` = "having drunk his fill of flowing Soma."
- `√pā- 1` (261 tokens): `pāti`, `pātu`, `pānti`, `pāta`, `pāsi`. RV 1.18.5 `dakṣiṇā pātv aṁhasaḥ` =
  "Daksina, Preserve that mortal from distress." RV 2.3.8 `pāntu` = "protect this holy Grass."

Note that this is the reverse of the numbering a reader may expect: many Sanskrit dictionaries give
`pā 1` = drink. This annotation does not, and the annotation is what the graph is built on.

**A second inversion, which the brief also has backwards.** The brief states `vid- 1` = "know" and
`vid- 2` = "find". The Zurich annotation is the opposite: `√vid- 1` is **find** (`vindati`,
`avindat`, `avindan` — RV 1.6.5 "Foundest the kine even in the cave") and `√vid- 2` is **know**
(`veda`, `vidvān`, `vidmá` — RV 1.4.3 `vidyāma` "may we be acquainted with"). `vid- 2` is also the
commoner of the two, at 391 tokens against 211. The two were kept apart as instructed, but under the
corrected senses: `vid- 1` → SEEKS, `vid- 2` → PERCEIVES.

---

## 4. The ten hardest decisions

**1. `√dhā- 1` (1,046 tokens): ESTABLISHES or GRANTS?**
Reading produced a tie — Griffith gives "give glorious strength" (RV 1.64.14) and "vouchsafe us
strength" (RV 1.2.9) alongside "on him have they laid splendour" (RV 1.73.4). Measurement broke it: a
locative appears in **30.6%** of dhā-1's padas against an 11.1% baseline (2.8x), while a dative
appears in only 19.3% against a 12.2% baseline (1.6x). Every unambiguous GRANTS root has the mirror
profile. **ESTABLISHES primary, GRANTS secondary**, disambiguated on a dative beneficiary with an
abstract good as patient. *Loss: roughly a fifth of these tokens are genuine bestowals recorded as
placement.*

**2. `√kr̥-` (1,207 tokens): the vaguest root in the corpus.**
Mapped to **CREATES at LOW confidence**, and the note says plainly that the mapping carries almost no
information. RV 1.1.6 `bhadraṁ kariṣyasi` is "whatever good thou wilt do", which Griffith renders
"wilt grant". A large share of tokens are fixed collocations (`namas kr̥-` "do homage", `araṁ kr̥-`
"make ready") where the predicate belongs to the noun. **The recommendation in the artefact is to
exclude `kr̥-` from action profiles by default, exactly as `IS_OR_BECOMES` is excluded.** Mapping it
rather than discarding it keeps the evidence countable; it is not a claim that the edge is useful.

**3. `√pā- 1` / `√pā- 2`.** See §3. Hard only because the key hides it.

**4. `√yuj-` (211 tokens): where does yoking go?**
Nearly every token is harnessing horses to a god's car (RV 1.6.1 "harness the bright, the ruddy
Steed"). **BINDS** is the only structural home and it is wrong in spirit: yoking is a relation of
harnessed service, not restraint. *This is the largest single loss after `kr̥-`: a query for "who
binds what" returns the Bay Horses of Indra.*

**5. `√sthā-` (402 tokens): standing is not sitting.**
DWELLS' gloss is "sits, abides, takes a seat". `sthā-` is a stance verb, and 57 of its tokens carry a
preverb that turns it into motion: `ā-sthā` "mount the chariot" (RV 1.164.3), `ud-sthā` "rise"
(RV 1.135.1), `vi-sthā` "spread out". **DWELLS on "abides", ESTABLISHES for the 6 CAUS tokens.** The
mapping most improved by consulting the particle.

**6. `√vr̥- 1` (179 tokens): the predicate inverts on the preverb.**
Bare `vr̥-` closes (RV 3.34.3 "Indra encompassed Vr̥tra"); `apa-vr̥-` opens (the Vala myth's uncovering
of the cow-pen). **BINDS primary, RELEASES secondary on `apa-`/`vi-`.** 47 of 179 tokens carry a
particle. *An extractor that ignores the particle here reports Indra as binding the waters he
released* — the single most consequential particle dependency in the map.

**7. `√vr̥- 2` (147 tokens): choosing has no class.**
`vr̥ṇīmahe` is the election of the divine priest — RV 1.12.1 "WE choose Agni the messenger, the
herald". The vocabulary has no class for a performative appointment. **DESIRES at LOW confidence**,
reached only through "prefers". The alternative was `UNMAPPED_ROOT`, which would silently delete the
hotr̥-election from the graph. I judged silence the worse error, but this is the closest call in the
file and an architect may reasonably reverse it.

**8. `√han-`: SLAYS or DEFEATS, or both?**
**SLAYS only.** RV 1.23.9 `hatá vr̥tram` is "strike Vr̥tra down" — an assertion of a kill. DEFEATS is
left to the corpus's dedicated subduing roots (`ji- 1` conquer, `sah-` prevail over, `tūrv-`
overpower, `randh-` subdue, 649 tokens between them), so both are not needed and giving `han-` a
DEFEATS reading would blur a distinction the corpus already draws lexically. *Loss: the 16 DES tokens
(`jighāṃsati`, "seeks to slay") are intent, not act, and neither the predicate nor the
ASSERTED/REQUESTED frame records that.*

**9. `√duh-` (148 tokens): milking as pressing.**
Structurally identical to `su-` — extract liquid from a source — but the source is the accusative
patient. Mapped to **PRESSES**, which merges cow-milking and the metaphorical milking of heaven with
Soma-pressing. *Anyone counting PRESSES must filter on the patient.* The alternative (POURS, on
Griffith's "pour fatness for the pious man", RV 6.70.2) loses the extraction, which is the point.

**10. `√vī-` (106 tokens) and `√sac-` (161 tokens): two roots the vocabulary has no room for.**
`vī-` is pursuit-and-desire at once — "I long to win thy love" (RV 8.4.17) but also "chased those
Dasyus" (RV 7.6.3) and "drives away sickness" (RV 1.35.9) — and its case profile is flat, so no
frame separates them. `sac-` is *accompaniment*: "Agni, be with us for our weal" (RV 1.1.9). Both are
LOW-confidence placements (DESIRES, MOVES_TO) made because no class fits.

**Honourable mention — a hard decision that turned out not to exist.** The brief offers `pinv-`
"swell" vs causative "make swell" as a case where the causative changes the predicate. It does not
apply: `pinv-` carries **no secondary-conjugation marking at all** in the annotation, and both the
intransitive "the broad waters swell their flood" (RV 7.34.3) and the transitive "fills full with
milk" (RV 9.68.3) are STRENGTHENS. The transitivity alternation lives in the stem and is invisible to
`secondary_conjugation`. Consulting that field for this root returns nothing.

---

## 5. Secondary conjugations and preverbs: what to consult, and what it buys

**Secondary conjugation** is marked on 2,237 root tokens (CAUS 793, DEN 680, INT 442, DES 322).

It changes the **predicate** for exactly two roots of consequence:

- **`√vanⁱ-`** — the strongest case. The desiderative `āvivāsati` is not "wishes to win" but the
  lexicalised "**invites**, seeks to win over (a god)": SEEKS → INVOKES, affecting **55 of 182
  tokens (30%)**.
- **`√sthā-`** — CAUS `sthāpaya-` "make stand": DWELLS → ESTABLISHES.

For a larger group it changes the **argument frame without changing the predicate**, which is a
subtler and more dangerous failure. `√vr̥dh-` is the clean example: `vāvr̥dhe` "he has waxed great"
and `vardhayanti` "they strengthen him" are both STRENGTHENS, but the nominative is the *grower* in
one and the *grower-maker* in the other. Same for `dhr̥-`, `sad-`, `vr̥t-`, `naś- 2`, `dhā- 2` and
`randh-`. An extractor that ignores CAUS here assigns the wrong role, not the wrong predicate — and a
role error is harder to notice downstream than a class error.

**It must not be read as "wants to X" by rule.** `√śak-` is **64% DES** (68 of 106 tokens) and its
desiderative `śikṣati` is the ordinary lexical "helps, assists" (RV 8.24.11 "So help us, Maghavan,
with thine assistance"). `√mr̥ḍ-` is 45% CAUS with no change of sense at all. INT never changes a
predicate anywhere in this map. The 680 DEN tokens are separate lemmas here, not markings on a base
root.

**Preverbs** are not in the lemma. 2,177 root tokens carry the `local particle` flag and the particle
is a separate token in the same pada, so `ā-gam` "come" and `gam` "go" share the root `gam`.

- **The one place the predicate inverts is `√vr̥- 1`** (BINDS ⇄ RELEASES). Nowhere else.
- **Materially improved** by the particle: `sthā-` (mount/rise/spread), `tr̥̄-` (`pra-tira` prolong vs
  `ati-tar` cross), `idh- 1` (94 of 185 tokens carry `sam-`), `i- 1` (132 tokens), `sad-` (78),
  `ruh-`, `vr̥t-`, `dhā- 1` (93), `bhr̥-` (52), `hu-` (52), `vī-` (`apa-vī` drive off), `yam-`
  (`ud-yam` raise).
- **Unaffected**, because their predicate is a property of the act and not of its direction: `as- 1`,
  `bhū-`, `su-` (press), `pū-` (purify), `stu-`, `gr̥̄- 1`, `r̥c-`, `hū-`, `juṣ-`, `mad-`, `īś-`,
  `vaś-`, `iṣ- 2`, `mr̥ḍ-`, `śak-`, `arṣ-`, `kṣar-`, `sru-`, `takṣ-`, `mā- 1` — none of which carries
  a particle on more than a handful of tokens.

**Recommendation**: record the particle as a qualifier on the assertion, as the brief anticipates.
Derive a predicate from it for `vr̥- 1` only.

**A caution about the particle index.** The `local particle` flag is on the *root* token, but the
particle itself is a separate token located by pada. Pada-level co-location is not attachment: while
sampling `√vī-` I saw three particles reported for a root that carries the flag on only 3 of its 106
tokens, because the particles in those padas belonged to other verbs. An implementer must bind the
particle by adjacency and sequence, not by pada membership.

---

## 6. Every place the mapping loses real information

Grouped by what is lost. All of these are recorded in the artefact's per-root `note`.

**A predicate that overstates.** `riṣ-` (65) "injure" → DESTROYS: there is no HARMS class, and
`riṣāma` "may we not be harmed" is not annihilation. Same for `riṣaṇy-`, `mr̥c-`, `dhūrv-`, `dambh-`.
`mī-` (75) "violate, transgress" → DESTROYS: `na minanti` "they do not violate the laws" is
transgression, and the commonest use is a *denial* that r̥ta has been infringed. `yudh-` (53) "fight"
→ DEFEATS asserts an outcome `yudhyati` does not. `nabh-` (40) is a single imprecatory refrain
(`nábhantām`, "let them burst") carrying a whole lemma.

**A predicate that flattens a distinction.** `yuj-` (211) yoking → BINDS. `sac-` (161) accompanying →
MOVES_TO. `vr̥- 2` (147) electing → DESIRES. `tan-` (137) stretching/weaving/performing → ESTABLISHES.
`duh-` (148) milking → PRESSES. `śās-` (47) commanding → SPEAKS drops the authority; RULES would drop
the utterance. `praś-` (56) asking → SPEAKS drops the interrogative force. `str̥̄-` (30) strewing the
*barhis* → ESTABLISHES drops the ritual specificity. `mr̥j-` (117) → PURIFIES drops the grooming of
horses. `pac-` (25) and `śrā-` (5) cooking → BURNS, because BURNS is the only heat class.

**A predicate that hides a role inversion.** `janⁱ-` (581) is the worst: `janayati` "X begets Y" and
`jāyate`/`jātaḥ` "X is born" are one lemma with **no** annotation to separate them, and 150 tokens are
`PTCP-ta` "born". *The AGENT slot must be left empty for the passive-inchoative forms or the graph
will claim that Indra begot himself.* `idh- 1` (185): active `indhate` = priests kindle Agni, passive
`idhyate` = Agni is kindled — ignore voice and the fire kindles the priest. `pū-` (591): MED
`pavate` = the Soma clarifies itself, ACT = the priests purify it. `vr̥dh-`, `dhr̥-`, `sad-`, `naś- 2`,
`dhā- 2` as in §5.

**A secondary predicate that is genuinely weak.** `rāj-` (67) SHINES/RULES is the least secure split
in the file: "ye shine forth" (RV 1.188.4) and "thou hast domination over all this world" (RV 5.81.5)
both use `vi-rāj`, so the disambiguation signal (a genitive naming a domain) is a heuristic, not a
rule.

**A whole verb class invented.** Ten roots of roaring, thundering, bellowing and neighing —
`krand-` (94), `svar-` (30), `rū-` (32), `vāś-` (32), `stanⁱ-` (22), `ghuṣ-` (17), `nad-` (12),
`rap-` (8), `mā- 2` (16), `svanⁱ-` (5), **268 tokens** in all — are filed under SPEAKS. The vocabulary
has no VOCALIZES class. *The utterance is real; the articulacy is not.* Parjanya's thunder and the
horse's neigh should not be returned by a query about divine speech.

**A whole verb class discarded.** The 102 individually adjudicated `UNMAPPED_ROOT` entries carry
1,876 tokens. The heaviest, with the reason in each case:

| root | tokens | gloss | why nothing fits |
|---|---|---|---|
| `añj-` | 112 | anoint, smear, adorn | no ANOINTS/ADORNS class. RV 9.45.3 "We balm thee, red of hue, with milk" — a core ritual act, and the largest single unmapped block. |
| `vas- 2` | 89 | clothe, wear | no class for dressing. Varuna's golden mail (RV 1.25.13), Soma "clothed in the robe of rivers" (RV 9.89.2). |
| `vr̥j-` | 69 | twist, wrest aside | torsion; `apa vr̥ṇaktu` is adjacent to PROTECTS but the root asserts the twisting. |
| `devay-` | 50 | be devout | denominative of *deva-*: piety as a standing attitude, with no patient and no event. |
| `bhī-` | 49 | fear | a state, whose bearer is not an agent. |
| `pr̥c-` / `śrī-` / `mikṣ-` | 49/30/12 | mix, blend | no class for mixing, including the ritual blending of Soma with milk. |
| `nam-` | 47 | bend, bow | physical and reverential bending share one lemma; `namasy-` carries the reverence and *is* mapped. |
| `ad-` + `aśⁱ-` `ghas-` `bhas-` `gras-` `gr̥̄- 2` `bhuj- 2` | 132 | eat, devour | **no EATS class.** DRINKS is lexically drink-only. Agni is the eater of oblations. |
| `hā- 2` | 44 | abandon, forsake | RV 8.7.31 "since ye left Indra all alone". RELEASES is a different act. |
| `prā-` | 39 | fill, pervade space | RV 1.115.1 "the Sun hath filled the air and earth and heaven". Distinct from `pr̥̄-` "fulfil a wish", which *is* mapped to GRANTS — the split is evidenced, not assumed. |

Also unmapped as classes: hatred/anger/patience as states (`dviṣ-`, `krudh-`, `hīḍ-`, `kṣam-`),
dying and decay (`mr̥-`, `jr̥̄-`, `das-`, `jas-`), sleep (`sas-`, `svap-`), bodily contact (`spr̥ś-`,
`mr̥ś-`, `rih-`, `niṃs-`, `svaj-`), theft and deceit (`muṣⁱ-`, `muṣāy-`, `dabh-`, `druh-`), throwing
(`as- 2`, `kṣip-`), trembling (`rej-`, `vip-`, `vij-`, `ej-`), dancing and play (`nr̥t-`, `krīḍ-` —
the Maruts' characteristic verb).

**A note on `as- 2` versus `vyadh-`,** since the two look similar and were decided differently.
`vyadh-` "pierce" is mapped to SLAYS because its patient is the *victim*; `as- 2` "shoot, hurl" is
unmapped because its patient is the *weapon*. The principle is that a predicate must not be assigned
when it would attach the wrong argument to the wrong role.

---

## 7. Predicates with no root — and the ones that nearly had none

**No predicate in the vocabulary ended up empty.** But three came close enough that the architect
should know exactly what they rest on.

| predicate | roots | tokens | standing |
|---|---|---|---|
| **HEALS** | 2 | **4** | **Exists only because of a rescue.** Both roots are below the frequency floor: `√bhiṣaj-` (2) and `√bhiṣajy-` (2). Had the floor been applied mechanically, **HEALS would have had no root at all.** The verse that justified the rescue: RV 8.79.2 "All that is bare he covers o'er, all that is sick he **medicines**; The blind man sees, the cripple walks." The vocabulary's own note anticipated a low Rigvedic count; the count is 4 tokens, 0.01% of the corpus. |
| **CURSES** | 5 | **35** | The thinnest mapped class. `śap-` (5), `nid-` (9), `aghāy-` (9), `dās-` (8), `gr̥h-` (4, rescued). And 1 of `śap-`'s 5 tokens is the *oath* sense, not the curse sense (RV 1.23.22 "If I have lied or falsely sworn") — so a fifth of the strongest root's evidence is misclassified by design. `nid-` is *reviling*, not imprecation; CURSES was chosen because SPEAKS would drop the hostility, which is the whole content. |
| **INVOKES** | **1** | 473 | Primary for `√hū-` alone. Four further roots reach it as a *secondary* predicate (`yā- 2`, `yāc-`, `īḍ-`, `vanⁱ-`, 438 tokens), so an implementer that ignores `secondary_predicate` will see the single most characteristic Vedic speech act reduced to one root. |

Also thin, and worth stating: **MEASURES** 2 roots / 95 tokens, **DRINKS** 2 / 421, **HEARS** 2 / 370,
**PRESSES** 2 / 737. Thin is not the same as weak — `su-` alone carries PRESSES at 589 tokens with
HIGH confidence — but a class resting on two lemmas will move sharply if either is re-adjudicated.

**Three classes are missing from the vocabulary**, and their absence is measurable as unmapped mass:
**EATS** (132 tokens, and Agni is the eater of oblations), **ANOINTS/ADORNS** (`añj-` alone is 112
tokens of a core ritual act), and **VOCALIZES** (268 tokens currently mislabelled SPEAKS). The
vocabulary is closed and I did not touch it; these are reported as findings for a future ontology
change, not as defects worked around.

### Predicate distribution (primary mapping, tokens)

```
MOVES_TO           3768  (37 roots)   DESTROYS            575  (26 roots)
IS_OR_BECOMES      2289  ( 3)         PROTECTS            520  ( 7)
CREATES            1824  ( 4)         SLAYS               504  ( 5)
ESTABLISHES        1587  (13)         BLESSES             501  ( 5)
PRAISES            1143  (16)         INVOKES             473  ( 1)
SEEKS              1109  (13)         EXHILARATES         426  ( 6)
GRANTS             1083  ( 9)         SEES                422  ( 5)
PERCEIVES          1057  (10)         DRINKS              421  ( 2)
DWELLS              950  ( 7)         FLOWS               387  ( 9)
SPEAKS              931  (17)         HEARS               370  ( 2)
CARRIES             916  ( 3)         RESCUES             352  ( 4)
STRENGTHENS         822  (15)         BURNS               346  ( 8)
PURIFIES            748  ( 6)         RELEASES            326  ( 3)
PRESSES             737  ( 2)         RECEIVES_OFFERING   275  ( 3)
LEADS               734  (12)         BUILDS              235  ( 7)
OFFERS              719  (10)         RULES               212  ( 4)
DEFEATS             649  (13)         POURS               204  (10)
BINDS               644  (12)         MEASURES             95  ( 2)
DESIRES             641  (13)         CURSES               35  ( 5)
SHINES              631  (11)         HEALS                 4  ( 2)
```

`MOVES_TO` at 11.8% of all root tokens confirms the vocabulary header's judgement that it is the
largest verb class in the corpus and that dropping it would have been a mistake. `IS_OR_BECOMES` at
7.2% (2,289 tokens across `as- 1`, `bhū-`, `jīv-`) is the second largest and asserts no action at
all — it is correctly excluded from action profiles by default.

### Confidence

124 HIGH / 154 MEDIUM / 64 LOW across the 342 mapped roots. The LOW band is dominated by `kr̥-`
(1,207 tokens on its own), then `sac-` (161), `vr̥- 2` (147), `tan-` (137), `vī-` (106).

### The three lowest-confidence mappings

1. **`√kr̥-` → CREATES (1,207 tokens).** A light verb doing duty as a content root. The mapping is
   almost information-free and the artefact recommends excluding it from action profiles by default.
2. **`√sac-` → MOVES_TO (161 tokens).** Accompaniment reported as motion, because no predicate
   expresses "be with". RV 1.1.9 `sácasva` is "Agni, be with us for our weal" — not travel.
3. **`√vr̥- 2` → DESIRES (147 tokens).** The ritual election of the divine priest reported as an
   appetite. The closest call in the file; `UNMAPPED_ROOT` was the alternative and would have deleted
   the hotr̥-election from the graph entirely.

---

## 8. What a researcher must not conclude from a predicate edge built this way

**This map assigns a verb class to a lemma. It is not a parse, and it is not a reading.**

1. **A predicate edge is not a syntactic claim.** The annotation underneath is *morphological*. There
   is no dependency parse, no clause boundary and no subject-verb link. What it supplies is
   co-location plus agreement: this metrical line contains a nominative deity and a third-person
   finite verb. In a one-clause pada that is usually the subject; in a two-clause pada it need not
   be. Nothing in this file improves that, and a consumer must state its own locality and agreement
   conditions and measure its own precision. **Do not present a co-location as a parse.**

2. **The predicate is the class of the verb, not the meaning of the verse.** "Indra CREATES" derived
   from `kr̥-` may mean he made a path, did homage, or brought about a state. "X BINDS Y" derived from
   `yuj-` probably means Y is a horse being harnessed. "X PRESSES Y" derived from `duh-` means Y is
   being milked.

3. **Absence of a predicate is not absence of the act.** 7.4% of root tokens produce no edge, and the
   gaps are systematic, not random: nobody EATS in this graph, nobody anoints, nobody is clothed,
   nobody chooses (except as DESIRES), nobody abandons. Six predicates the brief offered — WIELDS,
   RIDES, MARRIES, BURIES, CREMATES, CONSECRATES — were already dropped from the vocabulary for want
   of a root, and this map does not restore them. A query returning zero says the *verbal layer* has
   nothing, not that the Rigveda has nothing.

4. **Counts are token counts, not event counts.** A formulaic hemistich repeated across a Mandala
   contributes once per occurrence. `nabh-`'s 40 tokens are one refrain. Roughly a third of `kr̥-`'s
   are fixed collocations.

5. **A REQUESTED edge is not an ASSERTED one, and the vocabulary has only those two frames.** A
   desiderative — "Indra *seeks to slay* Vr̥tra" — has no frame of its own and will surface as an
   asserted killing. About 322 DES tokens are affected corpus-wide.

6. **Secondary predicates are conditional, and half of them rest on heuristics.** An implementer who
   drops `secondary_predicate` loses 1,046 tokens of GRANTS, 438 of INVOKES, 402 of ESTABLISHES and
   309 of BINDS. One who applies them uncritically will over-apply `rāj-` → RULES, where the stated
   signal is weak.

7. **This is a model adjudication, not a scholarly edition.** `adjudicator: MODEL_ADJUDICATED`. The
   roots and their sense divisions are the Zurich annotators' manual work and are high-quality
   evidence; the *assignment of each root to a predicate class* is mine, checked against 75 roots'
   worth of verses and against the case-frame statistics reported above, and unreviewed by a
   Vedicist. The 64 LOW-confidence mappings in particular should be read as proposals. There is still
   no human gold set for this layer.

8. **One lemma the annotation itself is unsure of.** `√mah- ?` carries a question mark in the
   annotation. It was rescued and mapped to PRAISES, and the uncertainty is inherited rather than
   laundered away.
