# VedaGraph — The 100-Question Answerability Benchmark (V3)

## BENCHMARK FROZEN

**This document is frozen for the remainder of Knowledge Model V3.** The wording of every question
Q1–Q100 and the acceptance criterion attached to it **may not be changed, softened, split, merged,
re-scoped or re-numbered** while V3 is in progress. The acceptance criteria were written *before* the
baseline evaluation was run, precisely so that later V3 work cannot be scored against a target that
has moved to meet it.

Three rules follow from the freeze and are binding:

1. **No re-wording.** If a question turns out to be badly posed, that is recorded as a defect of the
   benchmark in the V3 close-out report. It is not fixed in place. Q1–Q50 are reproduced **verbatim**
   from `VEDAGRAPH_50_KILLER_QUESTIONS.md` / `VEDAGRAPH_50_KILLER_QUESTIONS_V2.md`, identical
   numbering, identical wording (verified by diff — the two predecessor documents already agree
   byte-for-byte on all 50 headings).
2. **No criterion relaxation.** A question is `FULLY_ANSWERABLE` only when the acceptance criterion
   printed here is met in full. Meeting most of it is `PARTIALLY_ANSWERABLE`.
3. **Additions only, and only after V3 closes.** Q101+ may be appended by a successor benchmark.
   Nothing in Q1–Q100 may be retired.

| Field | Value |
| --- | --- |
| Benchmark version | V3 |
| Frozen on | 2026-09-09 |
| Frozen against commit | `bb27f3c` (branch `semantic-pilot-v1`) |
| Predecessors | `VEDAGRAPH_50_KILLER_QUESTIONS.md` (V1), `VEDAGRAPH_50_KILLER_QUESTIONS_V2.md` (V2) |
| Baseline evaluation | `VEDAGRAPH_100_QUESTION_BASELINE_V3.md` |
| Author role | Agent K — query-answerability evaluator (did not author V2) |

---

## The four verdict states

The V1/V2 three-state scheme is extended with a fourth, and the fourth is **not** a sub-grade of
`PARTIALLY_ANSWERABLE`. It is a distinct and worse failure.

| Verdict | Definition |
| --- | --- |
| `FULLY_ANSWERABLE` | A query returns a correct, complete, non-misleading answer over the corpus the question names, with evidence or provenance attached. |
| `PARTIALLY_ANSWERABLE` | A query returns something real but incomplete, or complete only for one Veda / one evidence mode. A stated caveat is sufficient to make the result safe. |
| `NOT_ANSWERABLE` | No query can return a meaningful answer. The dimension the question asks about is absent from the graph. |
| `MISLEADING` | **A first-class failure state.** A query returns a confident-looking answer that a researcher would reasonably read as true and which is actually wrong or unwarranted. A caveat is *not* sufficient, because the reader who runs the obvious query never sees the caveat. |

The three canonical shapes of a `MISLEADING` answer, for use in grading:

- **Inherited-as-per-verse.** A count presents container-scoped (sūkta-wide) attribution as if it
  were a per-verse statement of the text.
- **Absent-layer-as-absent-text.** A cross-Veda comparison in which one Veda's zero is a missing
  annotation layer, not an absence in the text.
- **Wrong-sense landing.** An edge that fires on one sense of a word (a vocative to a god) but is
  asserted onto an entity of another sense (the impersonal noun), or a typed-label query that omits
  the single most important member of the class it claims to enumerate.

A question is graded `MISLEADING` when the **substantive content** of the obvious answer is wrong —
its top-ranked members, its zeros, or its class membership. It is graded `PARTIALLY_ANSWERABLE` when
the content is directionally right but thin, one-Veda, or small-N in a way the rows themselves make
visible.

---

## How to read an acceptance criterion

Each criterion is written as a checklist. Every clause must hold. Clauses are of five recurring kinds
and the vocabulary is fixed:

- **Corpus completeness** — the answer must cover the corpus the question names. If the question says
  "the four Vedas", an RV-only answer fails.
- **Evidence attachment** — every returned row must carry a locator (passage key) plus the textual
  span or the named external source that licenses it.
- **Precision honesty** — where attribution is container-scoped, the row must say so, or the query
  must be restricted to verse-specific attribution and the recall cost stated.
- **Recall statement** — any frequency, prominence, ranking, centrality or similarity claim must be
  accompanied by a measured precision/recall figure against a human-annotated set. An unmeasured
  lower bound is not an answer to a "which is most/least" question.
- **Falsifiability** — the answer must name what observation would overturn it.

---

# PART 1 — Q1 to Q50 (carried verbatim from V1/V2)

### 1. How does Indra's role differ across the four Vedas?
**Acceptance:** Indra must be locatable in all four Vedas by name (not by a proxy noun), with a
functional characterisation per Veda derived from per-verse evidence, and the per-Veda counts must be
normalised for corpus size. A row set in which AV/SV/YV are zero fails, and fails as `MISLEADING`
unless the zero is explicitly typed as "layer absent" rather than "not attested".

### 2. Which Rishi families invoke Agni most?
**Acceptance:** A `RishiFamily` level must exist and be populated, seer names must be decomposed into
patronymic and personal name, and the leaderboard must be computed on verse-specific attribution with
the inherited-inclusive figure shown alongside it. The two must be presented together or the strict
one alone.

### 3. Which concepts are most strongly associated with Varuna?
**Acceptance:** A ranked concept list for Varuṇa across all four Vedas, computed on verse-specific
attribution, with a measured recall figure for the concept layer, and stable under the choice of
concept layer (i.e. the same ranking from either passage→concept layer, or one layer marked
authoritative).

### 4. What offerings are associated with each deity?
**Acceptance:** A deity→offering relation asserted per verse from the text (not inferred from
co-occurrence in the same verse), covering all four Vedas, with the offering vocabulary large enough
to distinguish oblation types. Two `Offering` nodes is not an offering vocabulary.

### 5. Which rituals invoke both Agni and Indra?
**Acceptance:** A ritual layer with more than a handful of named rites, per-verse deity attribution
permitting more than one deity per verse, and a query that returns rites rather than the empty set.
A zero result must be distinguishable from "the corpus model forbids two deities per verse".

### 6. Which Rigvedic verses are reused in Samaveda?
**Acceptance:** A directional reuse edge for every SV verse that has an RV source, with a per-pair
similarity metric and the Sanskrit spans on both sides, and a statement of what fraction of the SV is
covered.

### 7. How are those verses transformed?
**Acceptance:** A transformation typology (word substitution, insertion, sandhi change, metre change,
musical insertion) populated on every reuse edge, not on a minority of them, with the differing spans
recoverable.

### 8. Which formulas occur across multiple Vedas?
**Acceptance:** A formula inventory with a per-Veda occurrence vector on every formula, and the
locators for each occurrence, covering all four Vedas.

### 9. Which crops occur in each Veda?
**Acceptance:** A crop vocabulary complete enough that a zero cell means absence from the text rather
than absence from the alias list, with the alias list per crop disclosed and a measured recall figure.

### 10. Which metals occur in each Veda?
**Acceptance:** Every metal named in the corpus carries the `Metal` label, no metal is reachable only
under a supertype, and the per-Veda counts are normalised for corpus size.

### 11. Which animals are associated with wealth?
**Acceptance:** An asserted association (not verse co-occurrence) between animal and wealth, with
recall measured, covering all four Vedas.

### 12. Which deities are associated with healing?
**Acceptance:** A healing-role assignment per deity that is stable under verse-specific filtering and
covers all four Vedas. A ranking that inverts when inherited attribution is removed fails.

### 13. Which Atharvaveda passages concern marriage?
**Acceptance:** Recall on AV Kāṇḍa 14 (the marriage book, 141 passages) must be measured and stated.
A result covering ~10% of the gold-standard book while presenting itself as the marriage verse set
fails as `MISLEADING`.

### 14. Which concern childbirth?
**Acceptance:** As Q13, against the AV's childbirth material, with recall stated.

### 15. Which concern disease?
**Acceptance:** A named-disease inventory in which every disease named in the AV is present as its own
entity — specifically including *takman* as a distinct entity, not folded into a generic disease
node — and in which causes (sorcery, ill-named beings) are typed separately from afflictions.

### 16. Which concern enemies/protection?
**Acceptance:** Per-Veda counts normalised for corpus size, with measured recall, over an
enemy/protection vocabulary that distinguishes human rival, demonic enemy, and apotropaic protection.

### 17. What concepts and actions surround Soma?
**Acceptance:** Soma-as-substance must be separated from Soma-as-deity per occurrence, and the
surrounding actions must come from a verb-argument layer, not from a list of abstract nouns.

### 18. What actions does Indra perform most often?
**Acceptance:** A verb-argument layer in which Indra is the recorded subject of a deed with an object,
covering the canonical deeds (Vṛtra-slaying, vajra-hurling, cow-releasing, waters-freeing), with
per-verse evidence.

### 19. Who are the Rishis most associated with Indra?
**Acceptance:** The leaderboard must be computed on verse-specific attribution, and the
inherited-inclusive leaderboard must not be the default answer. Since V2 measured naive 217 against
strict 1 for the same seer, any answer that does not surface both fails.

### 20. What roles does Agni have besides physical fire?
**Acceptance:** Role assignment per occurrence (this verse treats Agni as priest; that one as
messenger), covering all four Vedas, not a constant per-deity axis vector.

### 21. Which concepts bridge Rigveda and Atharvaveda?
**Acceptance:** A bridging measure with a chance baseline, computed on one authoritative concept
layer with measured recall, over a vocabulary that includes theonyms.

### 22. Which passages are lexically different but conceptually similar?
**Acceptance:** A non-lexical similarity measure (embedding or human-annotated semantic type) so that
"conceptually similar" is not operationalised as "shares a word".

### 23. What deity communities emerge from the corpus?
**Acceptance:** Communities computed from genuine co-occurrence of deities in verses, not from
decomposing dual-deity Anukramaṇī labels, covering all four Vedas.

### 24. What differs between Rigvedic family books and later material?
**Acceptance:** A stratigraphic dimension on `Passage` (or an explicit, sourced maṇḍala-stratum map),
plus measured-recall concept counts, so that the comparison is diachronic rather than positional.

### 25. Which ritual objects recur most?
**Acceptance:** A ritual-implement class that excludes chariots and thunderbolts, includes the
Yajurvedic apparatus at plausible frequency, and is complete enough that `yūpa` and `vedi` counts are
not an order of magnitude below the text.

### 26. Which rivers occur with which clans?
**Acceptance:** Every river named in the corpus carries the `River` label — specifically including
Sarasvatī — the generic noun *sindhu* is separated from named hydronyms, and river↔clan association is
asserted rather than inferred from co-occurrence.

### 27. Which formula families spread across Vedas?
**Acceptance:** A formula *family* construct (a grouping of related formula strings under a stem or
parent), not a list of individually normalised strings.

### 28. Where do competing interpretations exist?
**Acceptance:** Competing interpretations *of the Vedic text*, attributed to named scholarly
positions, with the evidence each side adduces. Disagreements about this dataset's construction do
not answer this question.

### 29. Which graph claims are textual and which are interpretive?
**Acceptance:** One field, present on 100% of relationships, that partitions textual from derived
from interpretive, with no legacy field able to produce a different partition for the same edges.

### 30. What evidence supports a civilizational/evolutionary claim?
**Acceptance:** A stratigraphic dimension plus measured-recall material-culture counts, so that a
claim about change over time is not resting on Veda-as-proxy-for-time.

### 31. Which substances are offered to which deities?
**Acceptance:** An asserted offering relation per verse (substance X offered to deity Y), covering all
four Vedas, stable under verse-specific filtering.

### 32. What purposes are rituals performed for?
**Acceptance:** A purpose relation on more than a handful of rites, sourced from the text or from a
named ritual manual, covering the Yajurvedic repertoire.

### 33. Which deities co-occur?
**Acceptance:** Co-occurrence from verses that attribute two or more deities, with a chance baseline.
Pairs generated by decomposing compound deity labels must be separately typed.

### 34. Which concepts co-occur?
**Acceptance:** One authoritative concept layer, measured recall, and a chance baseline so that
"co-occur" is a finding rather than a frequency product.

### 35. Which deities are connected through common Rishis?
**Acceptance:** Computed on verse-specific seer and deity attribution, with a `RishiFamily` level, and
extended beyond the Rigveda or explicitly scoped to it in the result.

### 36. Which concepts increase/decrease in relative prominence by corpus layer?
**Acceptance:** A corpus-layer dimension that is not "Veda", measured-recall concept counts, and a
significance statement on each reported change.

### 37. Which mantras are central bridges between concept communities?
**Acceptance:** Centrality computed on one authoritative layer with measured recall, robust to the
layer choice, and not dominated by an annotation layer that exists for only one Veda.

### 38. Which deities have the widest functional range?
**Acceptance:** Functional range measured from per-occurrence role assignment, with compound
Anukramaṇī labels excluded or resolved to their constituents, and the deity's attested volume shown
alongside its range.

### 39. Which rituals have the most complex dependency structure?
**Acceptance:** A procedural ritual layer with ordering and prerequisite relations populated
(`PRECEDES`, `REQUIRES`, `HAS_STEP`, `PART_OF`), over the Yajurvedic repertoire.

### 40. Which objects/weapons belong to which deity narratives?
**Acceptance:** A `Weapon` class containing the corpus's actual weapons — the `vajra` above all — and
a narrative or agentive layer that ties weapon to deity as instrument rather than as co-mention.

### 41. Which natural phenomena are personified as deities?
**Acceptance:** An explicit personification relation between the phenomenon entity and the deity node,
populated for every such pair, so that the answer does not depend on string-matching an inflected
label.

### 42. Which deity names/epithets occur in which contexts?
**Acceptance:** An epithet occurrence layer linking epithets to passages, over an epithet inventory
covering a substantial share of the deity repertoire, with epithet-qualified deity labels linked to
their base deity.

### 43. How does Rudra's corpus profile differ by Veda?
**Acceptance:** Rudra locatable in all four Vedas by name, with per-Veda profiles normalised for
corpus size.

### 44. How does Varuna's corpus profile differ from Indra's?
**Acceptance:** Both deities profiled across all four Vedas on per-verse evidence, with the volume
asymmetry (Indra ≫ Varuṇa) controlled for rather than reported as a difference in profile.

### 45. How does Soma behave as deity vs substance?
**Acceptance:** A per-occurrence sense decision for every soma token, internally consistent across
sandhi variants of the same form, with a measured accuracy figure.

### 46. How does Agni behave as deity vs fire vs ritual medium?
**Acceptance:** A per-occurrence three-way sense decision with a measured accuracy figure. A cross-tab
of two independent matchers is not a disambiguation.

### 47. Which passages support healing practices?
**Acceptance:** Rows whose grade travels with them, so a curated interpretive assertion is
typographically distinguishable from a source-stated fact; plus a healing-practice vocabulary
(amulet, plant, water, spell) tied to the affliction.

### 48. Which passages concern prosperity/cattle/agriculture?
**Acceptance:** One authoritative concept layer, measured recall, per-Veda normalisation.

### 49. Which cross-Veda passages express similar ideas without textual reuse?
**Acceptance:** A non-lexical similarity measure. Shared-entity overlap on a layer with mean degree
under 2 cannot separate conceptual similarity from chance.

### 50. What are the strongest evidence-backed transformations across the four Vedas?
**Acceptance:** Directional, typed transformation edges for all six Veda pairs — not one — with the
typology populated on all of them and the differing spans recoverable.

---

# PART 2 — Q51 to Q100 (new in V3)

These fifty are deliberately harder than Q1–Q50. Where Q1–Q50 mostly ask *what does the corpus
contain*, Q51–Q100 mostly ask *what can be defended, and how would you know if it were wrong*. Many
are designed so that the obvious query returns a plausible table; the acceptance criterion is what
separates the table from the answer.

### 51. Which actions most distinguish Indra from Varuṇa — i.e. which deeds are attested for one and not the other?
**Why it is hard.** It requires a verb-argument layer (who did what to whom), a way to reach both
deities by name, and a contrast measure that controls for the fact that Indra is attested roughly
thirty times more often than Varuṇa. Every one of the three is a separate capability.
**Acceptance:** A ranked list of deeds with a distinctiveness statistic (log-odds, PMI or equivalent)
computed over a verb-argument layer in which each deity is the recorded subject, each row carrying at
least one per-verse locator and span, and the statistic controlling for base rate. A table of abstract
nouns co-occurring in the same verse does not qualify.

### 52. Which deity changes functional profile most across corpus divisions (RV maṇḍala, AV kāṇḍa, YV adhyāya, SV ārcika)?
**Why it is hard.** A "functional profile" must be assigned per occurrence, not carried as a constant
on the deity node — otherwise the measured variation is entirely the variation in which deity is
attributed where, and the profile itself never moves. It also needs deity attribution to exist outside
the Rigveda.
**Acceptance:** Per-occurrence functional role assignment, aggregated by division, for at least the
twenty most-attested deities across all four Vedas, with a divergence statistic per deity and a
significance test. Constant per-deity axis vectors fail by construction.

### 53. Which concepts connect Agni and Soma by a route that is not simple lexical co-occurrence?
**Why it is hard.** The obvious route is "verses that mention both", which is lexical by definition.
A non-lexical connector requires either an asserted semantic relation between concepts or a
distributional model, and it requires the connector not to be a word that appears in the same verse.
**Acceptance:** A ranked connector list produced by a measure that excludes same-verse token
co-occurrence — e.g. concept-to-concept asserted relations, or second-order distributional similarity
with a chance baseline — with per-connector evidence and a stated falsifier.

### 54. Which entities act as bridges between the ritual sub-graph and the cosmological sub-graph?
**Why it is hard.** It presupposes that "ritual" and "cosmology" are declared domains in the ontology
with enough members to constitute sub-graphs, and that a bridge measure exists which is not dominated
by whichever annotation layer happens to be largest.
**Acceptance:** An explicit ritual/cosmology partition covering a substantial share of the entity
registry (not a dozen nodes), a bridge or betweenness measure computed on one authoritative layer with
measured recall, and a demonstration that the ranking is stable under the alternative layer.

### 55. Which human concerns dominate the Atharvaveda relative to the other Vedas, normalised per 1,000 mantras?
**Why it is hard.** The AV's concern repertoire is large — fever, worms, rivals, debt, childbirth,
cattle, kingship, sleep, hair, dice, snakes — and any answer is only as good as the breadth of the
concern vocabulary. A four-item vocabulary produces a real ratio and a false picture of what the AV is
about.
**Acceptance:** A concern vocabulary broad enough to cover the AV's principal thematic books (order
tens of concerns, with the AV's disease, sorcery, statecraft, and domestic-rite material each
represented), per-1,000-mantra normalisation, measured recall per concern, and a significance
statement on each AV/other-Veda ratio.

### 56. Which Yajurvedic rituals have the richest object/offering networks?
**Why it is hard.** The Yajurveda is the ritual Veda; its rites (agnicayana, aśvamedha, vājapeya,
darśapūrṇamāsa, rājasūya) are named in the text and elaborated in the Brāhmaṇas. Answering requires a
rite inventory of that scale and an asserted apparatus relation per rite.
**Acceptance:** A YV rite inventory at the scale of the corpus's actual named rites, each with asserted
`USES_OBJECT` / `USES_OFFERING` / `USES_SUBSTANCE` edges carrying per-verse or named-manual evidence,
and a network-richness measure comparable across rites.

### 57. Which formula families occur in three or four Vedas, where a family is a set of related formula strings rather than one normalised string?
**Why it is hard.** The graph's formula layer keys on exact normalised strings, so a formula and its
one-word variant are two unrelated nodes. Family membership requires a grouping construct and a
principled relatedness threshold.
**Acceptance:** A populated family/cluster construct over the formula inventory, with each family's
per-Veda distribution, the member strings, and the relatedness criterion stated and reproducible.

### 58. Which lexical forms are reused across Vedas while their semantic function changes?
**Why it is hard.** Detecting a function change requires a function assignment that is independent of
the wording. If function is inferred from the words in the verse, then a verse reused verbatim will
always show an unchanged function, and the query answers "never".
**Acceptance:** A function or role assignment per occurrence that is independent of the token
inventory (ritual application, addressee, speech act), applied to reused verse pairs, with the changed
pairs listed and evidence on both sides.

### 59. Which passage pairs have the strongest evidence of *directional* textual reuse — borrower versus source, rather than symmetric similarity?
**Why it is hard.** Direction is not recoverable from a similarity score. It requires either an
argued chronological prior, or an asymmetry in the evidence (a metrical defect repaired, a word
misunderstood), recorded per pair.
**Acceptance:** Direction asserted per pair with the reason for that direction recorded on the edge,
available for all six Veda pairs, plus a similarity metric and the spans. A single global prior
applied to one Veda pair is not per-pair evidence.

### 60. Which passage pairs share ritual function without sharing text?
**Why it is hard.** It needs a ritual-function assignment with real recall, and it needs the pair set
to be more than the cross-product of a small lexical probe.
**Acceptance:** Ritual-function assignment with measured recall against a named ritual manual
(Kauśika-sūtra for the AV, a Śrautasūtra for the YV), pairs reported with the function and both
locators, and the pair count corrected for the cross-product effect.

### 61. Which Devatās are associated with which specific offerings, on per-verse source-stated evidence?
**Why it is hard.** This is Q4 with the two loopholes closed: no container-inherited attribution, and
no co-occurrence standing in for an offering relation.
**Acceptance:** Deity→offering edges whose evidence is a per-verse textual span naming both, over an
offering vocabulary large enough to distinguish oblation types, covering all four Vedas.

### 62. Which Rishis show the broadest deity range, after removing sūkta-inherited attribution?
**Why it is hard.** Only 4.5% of seer attribution is verse-specific, so the strict answer is computed
on a twentieth of the data and its top ranks are dominated by anomalies (deified seers, collective
attributions). The honest answer must report both and explain the divergence.
**Acceptance:** Strict and naive ranges reported together, with the strict computation's coverage
stated as a fraction, non-personal seer labels (`devāḥ`, `indraḥ`, `brahma`) typed as such, and a
`RishiFamily` roll-up.

### 63. Which deity pairs co-occur significantly above a chance baseline?
**Why it is hard.** "Significantly above baseline" requires an expected value, which requires a
population model of how deities are distributed over verses. It also requires that a verse be *able*
to carry two deities.
**Acceptance:** Observed and expected co-occurrence counts per pair with a named significance
statistic and a multiple-comparison correction, computed over verses that genuinely attest more than
one deity, with pairs derived from compound-label decomposition excluded or separately reported.

### 64. Which concepts are attested in exactly one Veda, and which in all four, at equal evidence strength?
**Why it is hard.** "Equal evidence strength" is the trap. An entity attested once in the Rigveda and
nowhere else is not a Rigveda-specific concept; it is a sample of size one. The answer needs a minimum
attestation threshold and a recall figure, and it needs the registry to contain the concepts that
matter.
**Acceptance:** Per-Veda attestation with a stated minimum count threshold, measured recall per
entity, per-Veda normalisation, and a registry that includes theonyms and the AV's disease vocabulary.

### 65. Which material-culture entities (metals, crops, animals, objects) shift distribution across the four Vedas, normalised for corpus size?
**Why it is hard.** Material-culture questions are the ones with real historical stakes, so the recall
requirement is strictest here. A shift is only a shift if the alias list is equally good in all four
Vedas, and the object class must not conflate chariots with ladles.
**Acceptance:** Per-1,000-mantra distributions with measured recall per entity per Veda, a significance
statement per reported shift, and a material-culture typing that separates ritual implement, vehicle,
weapon, ornament and foodstuff.

### 66. Which passages connect a healing act with a named divine invocation in the same verse?
**Why it is hard.** The healing material is overwhelmingly Atharvavedic and the divine-invocation
layer is Rigvedic. The two do not overlap, so the natural query returns a table in which the AV
contributes healing verses with no deity and the RV contributes deities.
**Acceptance:** Deity invocation attested per verse in all four Vedas, a healing-act relation distinct
from mentioning an affliction, and the joined rows carrying both spans.

### 67. Which ritual actions link a substance, an object and a Devatā in one asserted event?
**Why it is hard.** It requires an event representation with roles — actor, instrument, material,
beneficiary — not three independent edges hanging off the same passage.
**Acceptance:** An event node or reified relation per occurrence, carrying at least three typed role
arguments plus a locator and span, at corpus scale rather than as a pilot.

### 68. Which deity epithets cluster with which actions?
**Why it is hard.** Epithets have no occurrence layer at all, so there is nothing to cluster. It also
needs the action side, i.e. Q51's verb-argument layer.
**Acceptance:** An epithet→passage occurrence layer over a substantial epithet inventory, joined to a
verb-argument layer, with a clustering statistic and per-cluster evidence.

### 69. Where does the same deity occur under different functional roles in different passages?
**Why it is hard.** Role must be a property of the occurrence, not of the deity. The graph's axis
model assigns roles to the deity node, which makes the answer to this question structurally "nowhere".
**Acceptance:** Per-occurrence role assignment with a measured accuracy figure, and the within-deity
role variance reported per deity across all four Vedas.

### 70. What evidence in the graph supports or refutes the claim that Indra's prominence declines and Rudra's or Viṣṇu's rises across the four Vedas?
**Why it is hard.** This is the single most-cited diachronic claim about the Vedic pantheon and it
needs exactly what the graph most lacks: the three deities reachable by name in all four Vedas, a
time dimension that is not "Veda", and a prominence measure with a confidence interval.
**Acceptance:** Per-division prominence series for Indra, Rudra and Viṣṇu across all four Vedas on
per-verse evidence, normalised, with confidence intervals, plus an explicit statement of what
observation would refute the trend.

### 71. Which historical or civilizational claims about Vedic society are strongly supported by graph evidence — metallurgy, agriculture, horse and chariot, settlement?
**Why it is hard.** These are the claims a graph of this kind exists to support, and they are exactly
where an unmeasured recall figure becomes a historical error. `ayas` appearing 11 times is either a
finding about metallurgy or an artefact of a six-alias probe, and nothing in the graph distinguishes
the two.
**Acceptance:** For each claim: a per-Veda normalised count, a measured recall figure for the
underlying alias lists, a significance statement, and a named falsifier. Claims must be about the
Vedic world, not about this dataset.

### 72. Which interpretive claims in the graph have conflicting evidence, and what exactly is the conflict?
**Why it is hard.** It needs an interpretive layer whose claims are *about the Vedas* and whose
conflicts are substantive rather than methodological, with the evidence each side adduces attached.
**Acceptance:** At least a dozen claims about Vedic content, attributed to named scholarly positions,
with typed `SUPPORTED_BY` and `CONTRADICTED_BY` evidence sets on both sides of each conflict, and the
conflict's subject stated.

### 73. Which graph conclusions depend primarily on the English translation layer, and how many edges would be lost if translation evidence were withdrawn?
**Why it is hard.** The answer depends on the evidence-basis labelling being correct on every edge.
An edge whose recorded evidence is an English quotation but whose basis field says otherwise makes the
audit silently under-report.
**Acceptance:** An evidence-basis field that is correct on 100% of relationships, verified by
inspecting the recorded evidence spans, plus a withdrawal simulation reporting edges and answers lost
per question.

### 74. Which conclusions survive Sanskrit-only filtering?
**Why it is hard.** The inverse of Q73 and it fails in the opposite direction: any edge derived from
Sanskrit but labelled `UNSPECIFIED` is discarded by a Sanskrit-only filter, so the surviving set is
too small rather than too large.
**Acceptance:** No relationship carries `UNSPECIFIED` evidence basis where its derivation is in fact
Sanskrit-based; a Sanskrit-only projection is queryable; and the per-question delta between the full
graph and the Sanskrit-only graph is reported.

### 75. Which connections disappear under source-explicit-only filtering?
**Why it is hard.** It asks the graph to grade itself. It is answerable only if the provenance
partition is complete and consistent, and it will produce an uncomfortable number.
**Acceptance:** A complete census of relationships by provenance layer, with the source-explicit
subset enumerated by type, target class and Veda, and an explicit statement of which of the 100
questions retain any answer at all under the filter.

### 76. Which semantic relationships have independent corroboration from two or more passages *and* two or more distinct evidence modes?
**Why it is hard.** "Independent" is the hard word. Two layers built by the same matcher over the same
tokens are not two modes, and a graph can look doubly-attested while being singly-derived.
**Acceptance:** A corroboration census that demonstrates mode independence (not nesting) for each
corroborated set, reports the corroborated and uncorroborated counts per relationship type, and states
which pairs of modes are genuinely independent.

### 77. Where is the graph uncertain — can a researcher retrieve a calibrated per-assertion confidence that has been validated against ground truth?
**Why it is hard.** A confidence number is easy; a *calibrated* one requires a labelled evaluation set
and a reliability curve. A pipeline constant presented as a confidence is worse than no confidence at
all, because it supports filtering.
**Acceptance:** A human-annotated evaluation set in the graph, per-relationship-type precision and
recall measured against it, a reliability diagram or equivalent showing that a confidence of 0.8 means
80% correct, and a mechanism preventing constant-valued confidence fields.

### 78. Which major entities have coverage too thin to support a claim about them?
**Why it is hard.** The graph can enumerate what it has. It cannot enumerate what a Vedicist would
expect it to have, so the entities with the worst coverage — the ones absent from the registry
entirely — are invisible to the query.
**Acceptance:** An expected-entity manifest sourced independently of the graph (a standard index or
concordance), joined against actual coverage, so that absent entities appear as rows with zero
coverage rather than not appearing.

### 79. Which Veda is underrepresented in each ontology dimension, expressed as coverage per 1,000 mantras?
**Why it is hard.** It is a meta-question, and its difficulty is completeness: it must cover every
dimension, and it must not present a dimension's absence as a low score.
**Acceptance:** A dimension × Veda matrix over every knowledge-bearing relationship type, normalised
per 1,000 mantras, with structural zeros distinguished from low coverage.

### 80. Which relationships are likely artifacts of inherited container metadata rather than statements of the text?
**Why it is hard.** Also meta, and also a completeness question: it must find every inheritance path,
including any that is not marked as one.
**Acceptance:** A complete census of container-inherited relationships by type and Veda, plus a
verification that no relationship type carries an unmarked inheritance path, plus per-container
homogeneity so a reader can tell "inherited and safe" from "inherited and doubtful".

### 81. Which cross-Veda connections come from literal reuse versus semantic resemblance?
**Why it is hard.** It requires both categories to exist. If every cross-Veda edge is lexical, the
partition returns 100/0 and reads as a finding about the corpus rather than about the pipeline.
**Acceptance:** Both a literal-reuse and a non-lexical resemblance edge population, each with its
method recorded, and the partition reported per Veda pair with a note on the resemblance measure's
recall.

### 82. Which formula families transform in the Sāmaveda, and how?
**Why it is hard.** Sāmavedic transformation is largely musical — stobha insertion, vowel extension,
melodic naming — and none of that is textual. A text-only graph will report "no transformation" for
the Veda whose whole identity is transformation.
**Acceptance:** A Sāmavedic musical layer (sāman names, stobhas, gāna assignment), joined to a family
construct, with transformation types populated on all reuse edges and the SV-side spans available.

### 83. Which Atharvavedic concerns reuse Rigvedic material, and which are AV-native?
**Why it is hard.** It needs a broad AV concern vocabulary (Q55) and a complete AV↔RV parallel layer,
and it needs the AV-native claim to be safe against the possibility that the parallel simply was not
detected.
**Acceptance:** Per-concern counts of AV passages with and without an RV parallel, over a broad
concern vocabulary, with the parallel layer's recall measured and the AV-native set reported with a
confidence bound.

### 84. Which crops, metals and animals occur in which Vedas and in which contexts — ritual versus non-ritual?
**Why it is hard.** The context dimension is the difficulty. Ritual context must be a property of the
passage, not inferred from whether a rite happens to be named in the same verse; on that inference
almost every verse is non-ritual and the answer inverts.
**Acceptance:** A ritual-context assignment per passage independent of same-verse rite mentions (from
a ritual manual, a liturgical index, or the YV/SV liturgical position), joined to measured-recall
material-culture counts.

### 85. Which rivers are treated as deity-like and which as geography, decided per occurrence?
**Why it is hard.** The decisive case is Sarasvatī, which is both, and the graph must be able to hold
both readings for one hydronym and choose per verse.
**Acceptance:** Every hydronym present as a river entity including Sarasvatī, the generic *sindhu*
separated from named rivers, and a per-occurrence deity/geography decision with a measured accuracy
figure.

### 86. Which concepts attach to more than one personification?
**Why it is hard.** It requires an explicit concept→personification relation, and it requires
compound and epithet-qualified deity labels to be resolved so that "Heaven and Earth", "Heaven, Earth
and the Aśvins", and "Earth and the midspace" are not three separate personifications of earth.
**Acceptance:** A populated personification relation, compound deity labels resolved to constituents,
epithet-qualified labels linked to their base deity, and the multi-personification concepts listed
with evidence.

### 87. How is Soma-as-deity distinguished from soma-as-substance, per occurrence?
**Why it is hard.** Q45 asked whether the two behave differently. This asks for the decision itself,
per token, and it is the strictest possible form of the word-sense problem in this corpus.
**Acceptance:** A per-token sense label, internally consistent across sandhi variants of the same
form, with a measured accuracy figure against human annotation, covering all four Vedas.

### 88. How is Agni-as-deity distinguished from fire-as-physical-phenomenon, per occurrence?
**Why it is hard.** As Q87, with a three-way rather than two-way distinction and with a graph-resident
claim already stating that the corpus does not lexically license the distinction.
**Acceptance:** As Q87, three-way (deity / physical fire / ritual medium), with measured accuracy, and
with the standing claim of lexical undifferentiation either retracted or shown not to block the
decision.

### 89. How does Vāc-as-deity relate to speech-as-concept?
**Why it is hard.** The asymmetry is extreme — a handful of hymns to the goddess against hundreds of
mentions of the noun — so any relation must be built from the small side and the large side must not
swamp it.
**Acceptance:** A per-occurrence sense decision for *vāc*, an explicit relation between the deity node
and the concept node, and a characterisation of the deity's profile computed on the deity occurrences
alone with the volume asymmetry stated.

### 90. Which rituals use which priestly roles?
**Why it is hard.** The Vedic priestly system is a named set of sixteen officiants organised into four
groups; the *hotṛ* and the *udgātṛ* are the two whose Veda-specific roles define the Sāmaveda and the
Rigveda respectively. Any answer omitting them is not partial, it is wrong.
**Acceptance:** A priestly-role inventory covering the classical officiant set — *hotṛ* and *udgātṛ*
included and correctly typed — joined to a rite inventory at corpus scale, with the role↔rite relation
sourced from text or from a named ritual manual.

### 91. What actions happen inside each ritual, in order?
**Why it is hard.** Order is the difficulty. A ritual is a sequence, and an inventory of apparatus is
not a sequence.
**Acceptance:** Populated ordering relations over ritual steps, per rite, with each step tied to an
action and to its textual or manual source, over the Yajurvedic repertoire.

### 92. Which objects are deity-specific — associated with exactly one deity above chance?
**Why it is hard.** "Above chance" needs a baseline; "exactly one deity" needs verse-specific
attribution; and the answer needs to survive the fact that the most deity-specific object in the
corpus (Indra's vajra) is not typed as an object of that kind.
**Acceptance:** Per-object deity association with observed and expected counts and a significance
statistic, computed on verse-specific attribution, over an object typing in which weapons and
instruments are correctly classed, covering all four Vedas.

### 93. Which weapons occur in which narratives?
**Why it is hard.** It needs a narrative layer — a way to say "this set of verses tells the
Vṛtra-slaying" — which is a level of structure above the passage and above the concept.
**Acceptance:** A named-narrative or myth-episode layer with passage membership, joined to a weapon
class containing the corpus's actual weapons, with the weapon's role in each narrative recorded.

### 94. Which conditions are treated by which Atharvavedic practices — amulet, plant, water, spell?
**Why it is hard.** It needs the affliction vocabulary to be complete and unconflated (takman as
itself), the practice vocabulary to exist as a class, and the treatment relation to be more than "both
words appear in this verse".
**Acceptance:** An unconflated affliction inventory including *takman* as a distinct entity, a
practice-type class, asserted treatment relations carrying per-verse spans, and the grade of each
assertion visible in the returned row.

### 95. Which social rites connect to which concepts and deities?
**Why it is hard.** The social-rite layer must have real recall against the AV's rite books, and the
deity side must exist outside the Rigveda or the deity column is empty for the very Veda that carries
the rites.
**Acceptance:** Rite assignment with measured recall against the AV's rite kāṇḍas, deity attribution
present in all four Vedas, and concept counts from one authoritative layer.

### 96. Which entities are central bridges in the graph, and is the ranking robust to the choice of concept layer?
**Why it is hard.** The robustness clause is the point. With two rival passage→concept layers and one
deity layer that exists for a single Veda, a centrality ranking is a statement about the annotation
history rather than about the corpus.
**Acceptance:** Centrality computed on one authoritative layer with measured recall, the same ranking
reproduced on the alternative layer with a rank-correlation figure reported, and the RV-only layers
either extended or excluded with the effect on the ranking shown.

### 97. Which communities emerge when the graph is restricted to high-confidence edges only?
**Why it is hard.** It presumes that the high-confidence tier carries semantic content. If the
top-quality tier contains only metre, seer and deity labels, the communities it yields are
bibliographic, and they will look thematic.
**Acceptance:** A high-confidence tier that contains passage→concept and passage→entity assertions,
communities computed on it, and a comparison against the full-graph communities with a partition
similarity figure.

### 98. Which graph paths are meaningful versus accidental — can a path be scored for interpretability?
**Why it is hard.** Nothing in a property graph distinguishes a path that a Vedicist would accept from
one that merely exists. A scoring function needs typed relation semantics and, realistically, a
human-judged set of paths to calibrate against.
**Acceptance:** A path-scoring function with a stated basis, calibrated against a human-judged sample
of paths, reporting a meaningfulness score per path, plus a demonstration that low-scoring paths are
in fact rejected by a domain reader.

### 99. What are the ten most defensible novel discoveries VedaGraph can make today, each with a query, an evidence count and a stated falsifier?
**Why it is hard.** "Novel" requires knowing the literature, "defensible" requires measured recall,
and "falsifier" requires the graph to record what would overturn a claim. A finding about the
dataset's own construction is not a discovery about the Vedas.
**Acceptance:** Ten claims about the Vedic corpus (not about this dataset), each with a reproducible
query, an evidence set of per-verse locators, a measured recall figure for the underlying layer, a
novelty statement referencing prior scholarship, and a named falsifier recorded in the graph.

### 100. Can the graph answer a compound research question end-to-end — "for each Veda, which deity receives which offering in service of which human concern, with per-verse evidence"?
**Why it is hard.** It is the integration test. It joins four dimensions that each fail differently:
deity attribution (Rigveda-only), offering vocabulary (two nodes), concern vocabulary (four nodes),
and per-verse evidence (a fifth of deity attribution). A join over four thin dimensions collapses to
almost nothing, and the near-empty result reads as a statement about the Vedas.
**Acceptance:** A non-degenerate result set for all four Vedas — order hundreds of rows, not single
digits — with each row carrying deity, offering, concern, Veda and at least one per-verse locator with
a span, and with the row count's relationship to each dimension's coverage stated so that a small
result cannot be misread as a small phenomenon.

---

## Frozen coverage map

The fifty new questions were derived from a seed list; this table records the mapping so that no
future pass can claim a seed was never covered.

| Seed theme | Question(s) |
| --- | --- |
| Actions distinguishing Indra from Varuṇa | 51 |
| Deity functional profile change across divisions | 52, 69, 70 |
| Agni–Soma non-lexical connectors | 53 |
| Ritual↔cosmology bridges | 54 |
| AV-dominant human concerns | 55, 83 |
| Yajurvedic ritual apparatus networks | 56, 91 |
| Formula families across Vedas / in Sāmaveda | 57, 82 |
| Form reused, function changed | 58 |
| Strongest textual-reuse evidence; direction | 59, 81 |
| Shared ritual function without shared text | 60 |
| Devatā↔offering associations | 61, 100 |
| Ṛṣi deity breadth | 62 |
| Deity pairs above chance | 63 |
| One-Veda versus universal concepts | 64 |
| Material-culture distribution shifts | 65, 71, 84 |
| Healing joined to divine invocation | 66, 94 |
| Substance + object + Devatā in one event | 67 |
| Epithets clustered with actions | 68 |
| Civilizational claims; conflicting claims | 71, 72 |
| Translation dependence / Sanskrit-only / source-explicit-only | 73, 74, 75 |
| Independent multi-passage, multi-mode evidence | 76 |
| Graph uncertainty; thin coverage; per-Veda gaps | 77, 78, 79 |
| Inherited-metadata artifacts | 80 |
| Rivers: deity-like versus geographic | 85 |
| Concepts with multiple personifications | 86 |
| Soma / Agni / Vāc sense splits | 87, 88, 89 |
| Priestly roles per ritual | 90 |
| Deity-specific objects; weapons in narratives | 92, 93 |
| Social rites → concepts and deities | 95 |
| Central bridges; high-confidence communities; path meaning | 96, 97, 98 |
| Ten defensible novel discoveries | 99 |
