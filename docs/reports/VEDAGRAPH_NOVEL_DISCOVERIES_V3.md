# Ten Graph-Derived Observations, V3

**What this document is.** Ten observations produced by querying the finished V3 graph, none
of which is hard-coded anywhere in it. Each is reproducible from the query given, each cites
its evidence, and each carries the caveat that would make it wrong to over-read.

**What it is not.** A list of discoveries about the Vedas. Every observation below is a
statement about *this graph's contents*, and the gap between that and a statement about
Vedic religion is exactly what the caveats are for. Where an observation is
interesting **because** it may be an artefact of the graph rather than a feature of the
corpus, that is said in the caveat and it is still worth recording — an honest description
of where a model bends is more useful than a confident claim it does not support.

**Runner.** All queries were executed against `bolt://localhost:7687` at
108,725 nodes / 260,502 relationships. `scripts/verify_v3_demonstrations.py` and
`scripts/report_knowledge_model_v3.py` reproduce the surrounding figures.

**A warning about one method.** Six of these ten rest on `MENTIONS_DEVATA`, whose
Rigvedic rows come from a manual scholarly morphological annotation and whose Samavedic,
Yajurvedic and Atharvavedic rows come from adjudicated surface matching. Those are
different claims with different error rates, and **52% of all mention edges (8,485 of
16,261) carry `referent_certainty = DEITY_AMBIGUOUS`**. Any observation resting on raw
mention counts inherits that. Where an observation would change under a
`DEITY_CERTAIN`-only filter, the caveat says so.

---

## 1. The Aśvins–Sarasvatī pairing is overwhelmingly non-Rigvedic

```cypher
MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata)
WHERE r.non_rv_passage_count > r.rv_passage_count AND r.passage_count >= 10
RETURN a.display_label, b.display_label, r.lift, r.rv_passage_count,
       r.non_rv_passage_count
ORDER BY r.lift DESC
```

| pair | lift | RV passages | non-RV passages |
|---|---|---|---|
| the Aśvins / Sarasvatī | **5.823** | **6** | **54** |
| Pūṣan / Savitṛ | 5.633 | 7 | 25 |
| Tvaṣṭṛ / Pūṣan | 5.146 | 4 | 6 |
| Bṛhaspati / Pūṣan | 4.132 | 6 | 14 |

**Why interesting.** The Aśvins and Sarasvatī co-occur 5.8× more often than their
individual frequencies predict, and **90% of that co-occurrence is outside the Rigveda** —
in a corpus where the Rigveda supplies 63% of all mantras and the great majority of the
mention layer. The pairing is therefore not a Rigvedic pattern that the other Vedas
inherit; it is concentrated where the Rigveda is not. Pūṣan appears in three of the four
pairs with this shape.

**Caveat, and it is heavy.** The Aśvins–Sarasvatī triad is a known feature of the
Sautrāmaṇī and the Vājasaneyi ritual material, so this may be one rite's vocabulary
appearing many times rather than a broad tendency. The lift statistic cannot tell those
apart. **What would overturn it:** finding that the 54 non-Rigvedic passages cluster into
one or two liturgical sequences. That check is not done here and should be done before the
observation is used for anything.

---

## 2. `witchcraft` is the only concept confined to a single Veda at scale

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Concept)
WITH c, collect(DISTINCT p.veda) AS vedas, count(DISTINCT p) AS mantras
WHERE size(vedas) = 1 AND mantras >= 15
RETURN c.preferred_label_en, vedas[0], mantras ORDER BY mantras DESC
```

Exactly one row: **`witchcraft`, Atharvaveda only, 65 mantras.**

**Why interesting.** Of 225 registry concepts, every single one attested in 15 or more
mantras appears in at least two Vedas — except this one. It is a quantitative statement of
the Atharvaveda's distinctiveness that does not depend on anyone's characterisation of the
Atharvaveda, and it survives the obvious objection that the AV is simply large (it is the
second-largest corpus here, so single-Veda concentration is not a small-sample effect).

**Caveat.** This is a statement about the *registry*, not the corpus: a concept absent
from the registry cannot appear in this result, and the concern vocabulary was authored
with Atharvavedic material specifically in view, which biases toward AV-specific entities
existing at all. The finding is that no *other* registry concept is similarly confined —
not that no other such concept exists in the texts.

---

## 3. Ten concepts are attested in all four Vedas, and they are the ritual core

```cypher
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Concept)
WITH c, collect(DISTINCT p.veda) AS vedas, count(DISTINCT p) AS mantras
WHERE size(vedas) = 4
RETURN c.preferred_label_en, mantras ORDER BY mantras DESC LIMIT 10
```

heaven 1,206 · soma juice 1,169 · fire 1,028 · wealth 885 · sacrifice 839 · cattle 757 ·
earth 712 · soma pressing 656 · speech 651 · waters 646

**Why interesting.** The universal set is not the philosophically abstract vocabulary and
not the historically distinctive vocabulary. It is cosmological locations (heaven, earth,
waters), the two ritual substances (soma, fire), the sacrifice itself, and what the
sacrifice is *for* (wealth, cattle). Whatever else separates these four collections, they
share a ritual and material core.

**Caveat.** Frequency here is mention count, and the alias sets differ in breadth between
concepts — `fire` has a larger alias set than most, so its rank is partly a property of
the lexicon. Read the membership of the set, not the ordering within it.

---

## 4. Some deities are asked to do things they are never described doing

```cypher
MATCH (d:Devata)-[:IS_ASKED_TO]->(a:ActionPredicate)
WHERE NOT (d)-[:PERFORMS_ACTION]->(a)
RETURN d.display_label, a.predicate ORDER BY d.display_label
```

Bṛhaspati is asked to `DRINKS`, `MOVES_TO` and `RECEIVES_OFFERING` and is described doing
none of them. Heaven-and-Earth are asked to `PROTECTS`, `ESTABLISHES`, `IS_OR_BECOMES`.
Indra-and-Agni (the dual deity) are asked to `HEARS`, `GRANTS`, `SEEKS`, `RELEASES`,
`RECEIVES_OFFERING`, `PERCEIVES`.

**Why interesting.** The graph distinguishes the *asserted* frame (the text says the god
did this) from the *requested* frame (the text asks the god to do this), by grammatical
mood in a manual morphological annotation. The asymmetry is therefore a fact about verbal
mood distribution per deity, not an interpretation — and it is the kind of question that
was simply unaskable before the agentive layer existed.

**Caveat, decisive here.** Every one of these has **n = 1**. A single imperative with no
matching indicative is exactly what sampling noise looks like, and the whole layer is
**Rigveda-only** (it derives from the annotation, which covers only the Rigveda). This
observation is offered as a demonstration that the question is now expressible, and
explicitly **not** as a finding about Bṛhaspati.

---

## 5. Fever is invoked against three different deities, one per charm

```cypher
MATCH (p:Passage)-[:TREATS]->(c:Condition)
MATCH (p)-[:MENTIONS_DEVATA]->(d:Devata)
RETURN p.canonical_citation, c.preferred_label_en, collect(DISTINCT d.display_label)
```

AVS 1.25.1 fever → **Agni** · AVS 1.25.3 fever → **Varuṇa** · AVS 11.2.26 fever →
**Rudra** · AVS 12.1.46 worms → Pṛthivī · AVS 12.2.19 headache → Agni · AVS 2.10.1
hereditary disease → Heaven-and-Earth, Varuṇa, Nirṛti

**Why interesting.** This is the Atharvavedic healing question working as a connected
evidence graph rather than a keyword search: condition, passage, and invoked deity, each
with a locator. That *takman* (fever) is addressed to three different deities in three
charms — and that Rudra, the deity most associated with disease in later tradition, is one
of them — is visible only because the fever concept was split out of a conflated
`yakṣma` node in this pass. Before V3, none of these six rows existed.

**Caveat.** `TREATS` is TIER_D by design: it asserts that the passage acts on the
affliction, which is a reading of the charm, not a statement the charm makes about itself.
`MENTIONS_DEVATA` co-occurrence in the same verse is not the same as the charm being
*addressed* to that deity.

---

## 6. Two soma rites share an apparatus vocabulary that nothing else touches

```cypher
MATCH (r:Ritual)-[:USES_OBJECT]->(o:Object)
WITH o, collect(DISTINCT r.display_label) AS rites, count(DISTINCT r) AS n
WHERE n >= 2 RETURN o.preferred_label_en, n, rites ORDER BY n DESC
```

`stone`, `strainer` and `cup` are shared by **soma pressing** and **soma cup drawing** and
by nothing else. `sacrificial post` is shared by **sacrifice** and **horse sacrifice**.
`kindling` by **sacrifice** and **the fire oblation**. `altar`, `offering ladle` and
`sacred grass` by **sacrifice** and **soma cup drawing**.

**Why interesting.** The apparatus partitions the rites into a soma complex and a
fire/offering complex, with the generic `sacrifice` bridging them — a structure nobody
declared. It emerges from eight independently authored rite records.

**Caveat.** Eight rites and 79 apparatus edges is a small, hand-curated layer, and the
partition could be an artefact of who authored which record. It is a hypothesis about the
graph's structure, not a result about Vedic ritual taxonomy.

---

## 7. `pāta svastibhiḥ sadā naḥ` is the corpus's most widely shared formula

```cypher
MATCH (f:FormulaFamily) WHERE f.veda_span = 4
RETURN f.representative_display_form, f.member_count, f.mantra_count
ORDER BY f.mantra_count DESC
```

| family | members | mantras | Vedas |
|---|---|---|---|
| `pāta svastibhiḥ sadā naḥ` | 6 | **93** | all four |
| `viśvā bhuvanā` | 14 | 60 | all four |
| `parame vyoman` | 4 | 53 | all four |
| `indra girvaṇaḥ` | 12 | 48 | all four |
| `brahmaṇas pate` | 7 | 41 | all four |

**Why interesting.** The `FormulaFamily` layer is new in V3, and this is what it was
built for: before it, `pāta svastibhiḥ sadā naḥ` and its five expansions were six unrelated
`Formula` nodes, and a reader counting cross-Veda formulas counted the same phrase six
times. The family makes "one phrase, 93 verses, four collections" a single object. That the
top item is a blessing-refrain rather than a doctrinal statement is itself worth noting.

**Caveat.** Family membership is **transitive** containment, not pairwise: 237 of 2,037
members do not directly contain their family's representative, and the edge carries
`contains_representative` so that the stricter subset is filterable. Four members rest on a
similarity threshold rather than containment and are graded TIER_D for that reason.

---

## 8. The graph's deity mention layer is more ambiguous than certain

```cypher
MATCH (d:Devata)<-[m:MENTIONS_DEVATA]-()
WITH d, count(m) AS total,
     sum(CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN 1 ELSE 0 END) AS amb
WHERE total >= 100
RETURN d.display_label, total, amb, round(100.0*amb/total) AS pct
ORDER BY pct DESC
```

| deity | mentions | ambiguous | % |
|---|---|---|---|
| Vāc, Speech | 302 | 302 | **100%** |
| the serpent | 100 | 100 | **100%** |
| the Waters | 761 | 743 | 98% |
| Sūrya | 689 | 668 | 97% |
| Pṛthivī | 666 | 648 | 97% |
| Yama | 204 | 198 | 97% |
| Mitra | 428 | 391 | 91% |
| Rudra | 216 | 183 | 85% |
| Indra | 3,196 | **0** | **0%** |

**Why interesting.** This is the graph measuring its own weakest point, and the ranking is
almost exactly the list of deity names that are also ordinary nouns: speech, the waters,
the sun, the earth, the serpent. Indra, whose name is a name and nothing else, is 0%.
`Vāc` is 100% ambiguous because *every* occurrence of the word could be the noun "speech" —
which is the honest answer, and is why the graph refuses to assert the goddess.

**Caveat.** `DEITY_AMBIGUOUS` is an upper bound on error, not a count of errors — it marks
mentions whose sense the evidence does not settle, most of which are probably correct. It
is a statement about what is *checkable*, and the per-deity precision needed to convert it
into an error rate is measured separately in the gold-set report.

---

## 9. Jaundice is treated in the Atharvaveda and named in the Rigveda

```cypher
MATCH (av:Passage {veda:'AV'})-[:TREATS]->(c:Condition)
WITH c, count(DISTINCT av) AS av_treatments
MATCH (rv:Passage {veda:'RV'})-[:MENTIONS_ENTITY]->(c)
RETURN c.preferred_label_en, av_treatments, count(DISTINCT rv) AS rv_mentions
```

One row: **jaundice — 4 Atharvavedic treatments, 2 Rigvedic mentions.**

**Why interesting.** Of every affliction the Atharvaveda treats, exactly one is also named
in the Rigveda. The Atharvaveda's medical vocabulary is almost entirely its own, and this
single overlap is the exception that makes the pattern visible.

**Caveat.** A negative result of this shape is only as good as the `Condition` registry
and its aliases, and the registry grew from 12 to 36 entities in this pass — so the "one
row" is a statement about a lexicon that is still expanding, and a broader affliction
vocabulary could easily produce more overlaps.

---

## 10. Every deity with substantial non-Rigvedic presence also has Rigvedic attribution

```cypher
MATCH (p:Passage)-[:MENTIONS_DEVATA]->(d:Devata) WHERE p.veda <> 'RV'
WITH d, count(DISTINCT p) AS non_rv_mentions
WHERE non_rv_mentions >= 20 AND COUNT { (d)<-[:HAS_DEVATA]-() } = 0
RETURN d.display_label, non_rv_mentions
```

**No rows.**

**Why interesting.** A negative result, and it is the most load-bearing one here. There is
no deity in this graph that the later collections name substantially while the Rigvedic
index ignores it entirely. Had there been, it would be evidence of a deity entering the
tradition after the Rigveda — a genuinely significant claim. There is not, so the graph
does not support that claim, and recording the absence is what stops someone later
asserting it from a thinner query.

**Caveat.** This is bounded by the deity registry, which was built from the Rigvedic
Anukramaṇī — so a deity named only in the Atharvaveda may have no `Devata` node to be
counted at all. The Atharvavedic index ascribes hymns with 324 *descriptors* that are
deliberately not modelled as deities, and **none of them resolves to a `Devata` node**
(`ASCRIBES_TO_DEVATA` = 0, a documented and quantified gap). So this result should be read
as *"within the Rigveda-derived deity set"*, and it cannot yet be read more widely than
that. Closing that gap is the single change most likely to overturn this observation.

---

## What is deliberately not claimed

No observation above is presented as evidence of chronological development. Several would
be read that way if the caveats were stripped — #1 and #10 especially — and the graph
carries per-Veda counts, not dates. The `InterpretiveClaim` layer exists for readings of
that kind, holds six claims, and every one of them is TIER_D.

Two of the ten (#4 and #6) rest on layers small enough that a single authoring decision
could move them, and both say so. One (#8) is a finding *about the graph's own reliability*
rather than about the corpus, which is why it is included: a graph that cannot say where it
is weakest is not usable for research.
