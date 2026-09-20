# Morphology and semantic roles — agent 9, Wave 2

The semantic layer was Rigveda-only. It now reaches all four Saṃhitās, and nothing about it
is a model reading a translation.

**Nothing has been imported.** The canonical graph is unchanged; every figure below is
*stageable*, measured out of `data/staging/semantic_roles/`, not out of the database.

## What the assessed set is

Section 32's requirement, satisfied literally: all 20,210 mantras were examined and each
one leaves this run in exactly one state with a stated reason. The manifest balances.

| | mantras |
|---|--:|
| candidates considered | **20,210** |
| accepted — at least one assertion | 14,235 |
| rejected — examined, reason is a property of the text or of source coverage | 5,965 |
| unresolved — source covers it, address could not be established | 10 |

`rejected.jsonl` carries one row per abstention with its reason, so "assessed and empty" is
now distinguishable from "never assessed" for this dimension. That was the prerequisite
Wave 0 named and no artifact before this one could satisfy it.

## Per Veda

| | RV | SV | YV | AV |
|---|--:|--:|--:|--:|
| population | 10,552 | 1,844 | 1,975 | 5,839 |
| **passages processed** | 10,552 | 1,844 | 1,975 | 5,839 |
| reachable by a morphological source | 10,552 | **0** | 784 | 4,439 |
| **tokens processed** | 164,758 | **0** | 15,687 | 71,252 |
| finite verb tokens | 23,622 | — | 2,594 | 10,881 |
| **passages with ≥1 assertion** | 10,150 | 216 | 574 | 3,295 |
| **assertions** | 22,192 | 372 | 1,543 | 6,167 |
| **distinct predicates** | 40 of 41 | 37 | 36 | 36 |
| **asserted role fillers** (parse-backed only) | 0 | 0 | 387 | 1,665 |
| non-importable role candidates (queue) | 28,341 | 0 | 599 | 3,085 |
| agent + predicate + patient together | 4,109 | 50 | 152 | 908 |
| **abstentions** | 402 | 1,628 | 1,401 | 2,544 |
| **uncertain** (staged at `VERIFIED_SEGMENT`) | 0 | 0 | 81 | 391 |
| **failed** | 0 | 0 | 0 | 10 |

Samavedic `tokens processed` is **0** and it is a measured zero over an enumerated search,
not an unknown: no morphological token of the Sāmaveda Saṃhitā exists in any public
resource. `proofs/sv_morphology_unavailable.json` is the record.

Rigvedic coverage moves from 2,542 of 10,552 mantras (24.1%) to 10,150 (96.2%) — the
previous layer's 21% was not a limit of the annotation, which covers all 10,552 passages.
It was a consequence of the schema limit described below: the old rule only emitted an
assertion when the agent resolved to a `:Devata`.

Assertions carrying agent, predicate and patient together go from a measured **0** to
**341** — all of them parse-backed. GAP-SEMANTICS-003's benchmark claim of 17 does not
reproduce and never did; the live count is 0, re-verified here with edge direction checked
first. An earlier version of this report claimed 5,219; that figure rested on the
case-scoped role rule which the Wave-3 correction below withdrew.

## Three derivations, never summed

| derivation | assertions | asserted role fillers | what it rests on |
|---|--:|--:|---|
| `MORPHOLOGY_RULE_PREDICATE_ONLY` | 28,370 | **0** | predicate, frame, verb surface and verb features, read off the finite verb token. Roles withheld: no parse covers these passages. |
| `TREEBANK_DEPREL` | 1,532 | **2,052** | the verb's own dependency children in DCS, using the treebank's `obl:goal` / `obl:source` / `obl:instr` / `obl:loc` subtype labels. |
| `CROSS_VEDA_TEXT_IDENTITY` | 372 | **0** | a Samavedic verse whose letter skeleton equals a Rigvedic verse's, given that verse's predicate and frame. |

These must never be added together on a product surface, and neither may be added to the
2,406 existing `MORPHOLOGY_RULE` or 2,459 `MODEL_EXTRACTION` assertions. The proposed
`role_derivation` property exists to make that mechanical.

**No model-assisted extraction was used.** The brief permits it with provenance; the
deterministic route reached 96% of the Rigveda and 74% of the source-reachable
Atharvaveda, so a model pass would have added weaker evidence over material already
covered. Nothing here is labelled as human annotation, and nothing here *is* human
annotation.

## The `:Devata`-only role endpoint, and what it costs

Measured from both sides. `proofs/devata_only_role_endpoint_cost.json`.

**From the live graph.** The existing `MORPHOLOGY_RULE` layer already hit this wall and
worked around it the worst possible way: its 2,406 assertions carry 1,364 patients, 366
instruments, 356 beneficiaries and 225 locations as **opaque string properties**, and zero
edges for any of them. 2,311 role fillers are present in the data and reachable by no
traversal. The schema told a pipeline to write prose.

**From this artifact.** Restated on the corrected layer. The argument is now *stronger*,
because it rests only on labels taken from a dependency parse rather than on the withdrawn
case rule — 2,052 asserted, parse-backed fillers:

| | fillers | share |
|---|--:|--:|
| a `:Devata` — the only thing today's schema can hold | 142 | 6.9% |
| **not representable at all** | **1,910** | **93.1%** |
| …of which resolve to an existing `:Concept`/`:DomainEntity` node | 245 | |
| …of which are the first- or second-person ritual participant | 298 | |
| …of which are an unregistered nominal or unresolved pronoun | 1,367 | |

Over the asserted layer *plus* the verification queue — 34,077 fillers, which is the size
of the role layer this corpus would support if the roles could be defended — the shape is
the same: 2,946 deities (8.7%) against **31,131 (91.4%) unrepresentable**.

The cost is two-layered and the layers need separating:

1. **No relationship type exists for the role at all.** 643 of the 2,052 asserted
   fillers (31.3%) fill BENEFICIARY, INSTRUMENT, LOCATION, SOURCE or GOAL — 11,344 over the
   asserted layer plus the queue. Three of those five are *declared roles in the project's
   own `action_predicates.yaml`*, named in the `argument_frame` of GRANTS, SLAYS, POURS,
   ESTABLISHES, CREATES, CARRIES, OFFERS, SPEAKS, MOVES_TO, FLOWS, SHINES and DWELLS. The
   schema has no edge type for any of them, whatever the endpoint.
2. **The two types that do exist are `:Devata`-only.** Of 1,409 asserted AGENT and PATIENT
   fillers, 116 are deities. **1,293 — 91.8% — cannot be attached** even though the edge
   type exists.

The sharpest single consequence, on the parse-backed layer alone: 111 of the 167 asserted
BENEFICIARY fillers are the first- or second-person ritual participant. *"Grant to us"* has a recipient and it is not a god. A role layer whose
endpoints are deities can state that a god acts, and never that a god acts **for
someone** — which is most of what the Saṃhitās say. That is why "a role layer that can
only say 'a god did it' is not a role layer" is the right reading, and it is now a number.

### The proposed additive extension

Additive only. No existing type changes name, direction or range; no existing edge is
rewritten; the current 4,865 assertions and their edges keep working, and a consumer who
wants only deity-to-deity events is unaffected.

- **One new label, `:RoleFiller`**, with `role`, `surface`, `lemma`, `case`, `upos`,
  `filler_type`, `proposed_role`, `evidence`, `derivation`.
- **`ASSERTION_ROLE`**, `:SemanticAssertion → :RoleFiller`, 0..n. The role is a *property*,
  so adding a role later needs no schema change and no migration.
- **`ROLE_FILLER_ENTITY`**, `:RoleFiller → :Devata|:Concept|:DomainEntity`, 0..1. Present
  only where the filler resolved. Every entity key this artifact references was resolved
  against the live graph — 37 `:Devata` and 81 `:Concept` across the asserted layer and the
  queue — so the endpoints already exist and none is invented. The projection is shipped:
  `role_fillers.jsonl`, 2,052 rows, parse-backed and importable.
- **`polarity`** on `:SemanticAssertion` (`POSITIVE|NEGATED|UNKNOWN`). See QA-3.
- **`role_derivation`** on `:SemanticAssertion`, so the five instruments cannot be summed.

Why reification rather than widening the range: a union range of Devata, Concept,
DomainEntity plus something to hold a pronoun is open-ended and unenforceable, and an
unenforceable range is exactly how the attribution axis in this project came to have three
disagreeing writers. One node per filler keeps the range closed at a single label and
carries the surface and case that make the role auditable.

## Samaveda morphology: unavailable, on my own enumeration

Confirmed, by independent enumeration rather than by inheriting Wave 0's conclusion.
Three comprehensive resources, three negatives, each reproducible from the recorded
method:

| resource | enumerated | Sāmaveda Saṃhitā |
|---|---|---|
| DCS CoNLL-U | **271 corpora**, via the git `trees` API on the `dcs` subtree, recursive, `truncated=false`, 23,576 entries | absent. Sāmavidhāna 46 files, Pañcaviṃśa 338, Jaiminīya 519, Drāhyāyaṇa 96 — the ritual literature is well served, the Saṃhitā is not there |
| UD_Sanskrit-Vedic | **57 texts**, 27,182 sentences, 206,440 tokens, every `citation_text` counted | absent. Only Sāmavedic text is `SVidhB`, 202 sentences |
| VedaWeb 2.0 | **7 texts**, `/api/texts` and `/api/resources` read in full | absent |

The `contents` API was not used: it caps at 1,000 entries and the Atharvavedic directory
holds 1,038 blobs, so it would have hidden kāṇḍas 16–19.

This is the `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE` case on evidence. Agent 5's finding was
checked: it located an **accented Ārcika text** (`सस्वरा पूर्णा`), which bears on
`GAP-MORPHOLOGY-006` and not on morphology. An accented text is not an analysis.

### What the Samaveda got instead

1,662 of 1,844 Ārcika verses carry a deterministic reuse or parallel edge to a Rigvedic
verse. Where the letter skeleton is **identical as a string**, the words are the same words
and the Rigvedic analysis of those words is transferred. 216 verses, 372 assertions.
Everything short of identity abstains, with the reason and the containment on its row.

The graph's own parallel layer carries 89 `EXACT_PARALLEL_OF` and 415 `VARIANT_OF` edges
between Samavedic and Rigvedic verses; letter identity reaches 216 verses. The two
disagree because the parallel layer folds sandhi and this does not — sandhi changes word boundaries, and a morphological analysis is per word, so a
sandhi-insensitive match is not a licence to transfer one.

The refusals are not uniform, and the distribution is the useful part:

| containment against the closest Rigvedic parallel | verses |
|---|--:|
| 0.99–1.00 | **311** |
| 0.95–0.99 | 798 |
| 0.90–0.95 | 273 |
| 0.80–0.90 | 51 |
| 0.60–0.80 | 3 |
| no parallel edge at all | 192 |

The 311 differ from their Rigvedic source by one or two letters. A philologist can say in
seconds whether the differing word changes the analysis. That is a bounded queue, not an
open problem.

Every projected row states that it concerns the Ārcika text only: the sung sāman, its
stobhas and its melodic text are a different object, and this layer says nothing about
them.

## Sources, with coverage as I measured it

**DCS CoNLL-U, CC BY 4.0** (verbatim in `dcs/data/conllu/readme.md`). 534 blobs fetched
from `raw.githubusercontent.com` at ref `master`, each SHA-256'd individually; the snapshot
id is the digest of the sorted digest list.

- **AVŚ 519 hymn files.** Hymns per kāṇḍa, tallied from filenames:
  35/36/31/40/31/142/118/10/10/10/10/5/4/2/18/9/1/4 for kāṇḍas 1–18, then **3 of 72** in
  kāṇḍa 19 and **none** of kāṇḍa 20. Those eighteen figures are this repository's Śaunaka
  spine exactly, which is the recension evidence.
- **VSM 15 adhyāya files** of 40 — 784 of our 1,975 verses.
- **Sāmaveda Saṃhitā: absent.**

**Zurich/VedaWeb Rigvedic annotation**, already in the repository at
`data/knowledge/rigveda_lexical_v1`. 10,552 passages, 164,758 tokens, 32,029 root tokens,
23,622 of them finite. **No dependency parse.**

**UD_Sanskrit-Vedic, CC BY-SA 4.0 — enumerated and set aside as non-additive.** It is not
an independent second witness: DCS carries a dependency parse on **2,160 of 9,105**
Atharvavedic sentences (23.7%) and **619 of 2,516** Vājasaneyi sentences (24.6%), against
UD's own 2,175 AVŚ and 622 VSM sentences, over 188 parsed AVŚ hymn files against UD's 185
distinct hymns. UD is the treebanked slice of DCS re-released. Ingesting it would add no
coverage, and an agreement figure between the two would measure a file format. **So no
cross-source agreement figure is claimed anywhere in this artifact.**

That holds for the *source*. It does **not** hold for the *rule*, and the adversarial
preflight below exploits the difference: the parsed quarter is a ground truth for the
case-scoped role rule even though it is not a second opinion about the text.

**VedaWeb 2.0, probed directly.** Two negatives and one positive, measured rather than
inherited:

- 7 texts, none of them the Sāmaveda.
- **`avs` carries no `textAnnotation` resource at all** — only hymn titles, TITUS
  plainText and the Whitney translation — while **`avp` does**. The Wave-0 trap is
  confirmed by measurement: the most permissively licensed annotated Atharvaveda on
  VedaWeb is the wrong śākhā, and nothing was fetched from it.
- **Incidental, and it belongs to a gap I own:** the `rv` text carries a `plainText`
  resource titled *"Lubotsky Padapatha (1997)"*. `GAP-MORPHOLOGY-003` records that the
  served Rigveda scope statement claims a Padapāṭha while all 44,276 `:TextVersion` nodes
  are `text_form='SAMHITA'`. **The source exists and is reachable.** Correcting the false
  claim in `works.yaml` is still the immediate obligation and is not my write surface.

## The predicate and role vocabulary: aligned, not paralleled

`data/registry/action_predicates.yaml` is used **unmodified** — 41 predicates, closed —
and `data/registry/action_root_map.yaml` is the root map. The brief's names map onto the
registry's rather than beside them:

| brief | used here | why |
|---|---|---|
| AGENT, PATIENT, INSTRUMENT, LOCATION | same | identical |
| RECIPIENT | **BENEFICIARY** | the registry already has this role, from the dative. One name, not two. |
| ACTION | `:ActionPredicate` | the registry's 41-member closed set is the ACTION dimension |
| SOURCE | **proposed** | the ablative. Not in the registry. Counted separately on every row and flagged `proposed_role: true`. 1,013 fillers. |
| GOAL | **proposed** | an accusative under a predicate whose own `argument_frame` has no PATIENT slot — MOVES_TO, FLOWS, SHINES, DWELLS. Derived from the registry's frames, not invented beside them. 3,072 fillers. |

The treebank names three of these itself: `obl:source`, `obl:goal` and `obl:instr` are DCS
labels and are used in preference to the case heuristic. `obl:goal` matters most — its
filler is usually an accusative, and a case rule would have filed every goal of motion as
a PATIENT.

`obl:temp` and `obl:soc` are deliberately given **no** role. Inventing a COMITATIVE to
hold `obl:soc` would be the parallel vocabulary the brief forbids.

## What refused, and why refusing was the point

Every rule that could have forced a wrong answer instead abstained and said so:

| refusal | RV | AV | YV |
|---|--:|--:|--:|
| homonym fold — two mapped predicates on one key | — | 1,147 | 165 |
| …after a preverb strip | — | 100 | 35 |
| particle-sensitive root, per the registry's own list | — | 312 | 131 |
| conjugation-sensitive root, per the registry's own list | — | 17 | 0 |
| root not in the Rigvedic map | — | 2,684 | 638 |
| `UNMAPPED_ROOT`, adjudicated in the root map | 1,173 | 454 | 82 |
| below the root map's frequency floor | 257 | — | — |
| nominative refused for number disagreement | 443 | 313 | 39 |
| sentence spanning a verse boundary | — | 13 | 0 |
| hymn refused below the skeleton match floor | — | 1 hymn | 0 |

The root map's own hazard list did real work. `pā` (drink / protect), `vid` (find / know),
`yā` (go / implore) and `i` (go / lead) are all refused outright, because a DCS lemma
carries no scholarly sense number and there is no signal to break the tie. Guessing would
have filed all Soma-drinking and all divine protection under one predicate — which is the
specific failure `ACTION_PREDICATE_ROOT_MAPPING_V3.md` was written to prevent.

**One rule I introduced and am flagging for a ruling.** Where a length-neutral key carries
two mapped predicates and one holds **≥95%** of the key's Rigvedic root tokens, it resolves
to that one, status `MAPPED_BY_DOMINANT_SENSE`, with the loser and the share named on the
assertion. 963 assertions in AV and 176 in YV rest on it — `kṛ` → CREATES at 0.9853,
`dhā` → ESTABLISHES at 0.9849, `dā` → GRANTS at 0.9738. It is a frequency prior, it is
labelled, and one filter drops all of it. `stṛ` at 0.7895 and `gṛ` at 0.7785 are refused
by the same rule.

## Alignment: DCS has no verse number, so the verse was recovered by text

DCS files are keyed at hymn level and carry no verse number, and the sentence blocks are
syntactic rather than metrical — AVŚ 1.1 has four verses and seven sentence groups, so the
base `sent_id` is a sub-verse unit and positional assignment is simply wrong. I checked
that first: grouping by base `sent_id` matched our verse count in only 38 of 519 AVŚ hymns
and 0 of 15 adhyāyas.

Instead each hymn's whole sentence sequence is aligned against that hymn's whole verse
sequence as two concatenated letter skeletons, and each sentence's verse is read off the
matching blocks. Floors: a sentence needs 0.60 of its own letters matched and 0.70 of those
inside one verse; a hymn is refused below 0.70 overall.

| | hymns/adhyāyas | aligned | sentences | addressed | unresolved |
|---|--:|--:|--:|--:|--:|
| AVŚ | 519 | 518 | 9,105 | 9,061 | 44 |
| VSM | 15 | 15 | 2,516 | 2,505 | 11 |

`mapping_confidence` is `EXACT` where every contributing sentence matched at ≥0.90 with all
matched characters inside one verse, `VERIFIED_SEGMENT` otherwise. 472 rows are
`VERIFIED_SEGMENT` — 391 Atharvavedic and 81 Yajurvedic; the weakest sentence match and
the weakest single-verse concentration are carried on every one of them.

## QA — and it is a model reading its own output

51 assertions drawn, 31 adversarially across eight strata that each exercise a rule which
could force a wrong answer, 20 at random; 44 adjudicated against the verse text and the
source sentence. **`MODEL_ADJUDICATED`, `claude-opus-5`. Zero human annotations.** The
repository has no human gold set for Vedic semantic roles —
`rigveda_semantic_gold_v1.jsonl` is 120 rows all `UNANNOTATED` — so **no precision figure
is claimed for any corpus**. 4 in 44 is a floor on the defect rate, not an estimate of it.

| | what it was | status |
|---|---|---|
| **QA-1** | AVŚ 14.2.22: the ritual spreading of the hide came out as DESTROYS | **closed in code** |
| **QA-2** | RV 8.48.10 `ayaṁ yaḥ somo ny adhāyy asme`: a passive verb's nominative labelled AGENT, making the deposited Soma the depositor | **closed in code** |
| **QA-3** | VSM 6.22 `mā apaḥ mā oṣadhīḥ hiṃsīḥ`: a prohibition came out as a *requested* SLAYS with the plants as PATIENT — the opposite of the verse | **mitigated, not closed** |
| **QA-4** | AVŚ 6.114.2: "we could not accomplish the sacrifice" came out as BLESSES | **open, inherited** |
| **QA-5** | the case-scoped rule attaches 24.8% of its role fillers across a clause boundary or to the wrong role, measured against the parse on 1,114 sentences | **closed by withdrawing the rule** — see the Wave-3 correction |

**QA-1's cause is a new hazard of the same shape as the one the root map names.** DCS never
writes a long vocalic liquid — measured: **0 of 1,651 distinct verb lemmas**. So its `stṛ`
is both Zurich's `str̥-` (lays low, DESTROYS, 8 tokens) and `str̥̄-` (strews the sacred
grass, ESTABLISHES, 30 tokens), two roots with *opposite* predicates. A key that looks
unambiguous and is not. DCS resolution now runs over a length-neutral bucket.

**QA-2** is the inversion the root map predicted in so many words — "an extractor that
assigns AGENT from any nominative will make the fire kindle the priest". A caution on the
assertion did not undo a wrong role on the filler, so the rule was changed: under
`voice=PASS` a nominative is PATIENT. 467 Rigvedic, 116 Atharvavedic and 9 Yajurvedic
case-scoped fillers moved, plus 28 `nsubj` fillers under a parsed passive.

**QA-3 cannot be closed in this artifact.** The predicate vocabulary has no polarity field
and exactly two frames, ASSERTED and REQUESTED. 2,061 assertions sit in the scope of a
negation or prohibition particle and now carry
`POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE` with the particle named, so they can be
excluded rather than read backwards. A `polarity` property is in the additive proposal.

**QA-4 was left open deliberately.** `action_root_map.yaml` maps `√śak-` to BLESSES on its
lexicalised desiderative "helps, teaches", which is defensible for the simplex and wrong
for `upa-śak` "be able to". Overriding a hand-adjudicated root map from a string operation
would be worse than the defect.

### Limitations the sample exposed that are not defects

- A **dative of purpose** is read as BENEFICIARY, because the registry defines BENEFICIARY
  as a dative. "for lasting might" becomes a beneficiary.
- A **first-person optative wish** is filed ASSERTED, because the two frames are ASSERTED
  and REQUESTED only. "may we be" is neither.
- **Pronoun referents are not resolved.** 2,250 AGENT and 2,412 PATIENT fillers are
  pronouns, many of them deities addressed as "thee". No coreference layer exists.
- **Directional and causative nuance is lost**, which the root map explicitly instructs:
  record the particle as a qualifier, do not derive a new predicate from it. So
  `pra-cyu` "moves away" is MOVES_TO and `ramay` "causes to rest" is DWELLS.
- **Compound members.** DCS splits a nominal compound into one token per member and only
  the last carries the case. Where a parse exists the members are now prepended, so the
  filler's surface is the whole compound; where no parse exists they cannot be.

## WAVE-3 CORRECTION — the case-scoped role rule was withdrawn, not annotated

The owner ruled the previous artifact superseded and not importable. This section is the
record; every table above reflects the corrected run.

### headline_before

| | before |
|---|--:|
| assertions | 30,274 |
| **asserted role fillers** | **51,231** |
| agent+predicate+patient triples | 5,219 |
| Rigvedic passages with an assertion | 10,150 of 10,552 |
| known error in asserted role fillers | **24.8%**, recorded in an `evaluation` block |

### The attack

Most load-bearing assumption: *a role read from morphological case beside a finite verb,
scoped to one pada or one sentence, is the role a dependency parse would assign.* 28,370 of
30,274 assertions rested on it.

A test was possible because the earlier claim that "no agreement figure can be computed"
was true of the **source** and false of the **rule**: 2,823 DCS sentences carry a
human-validated parse, so the rule can be run on exactly those and scored. Not seeing that
was a gap in my own evaluation design.

Result: raw precision **0.4855**. Decomposed, **24.8% of emitted fillers were wrong** — 623
attached across a clause boundary, 50 given the wrong role — while a further 21.4% were a
second token inside one argument. The deployed gate could not see it, because it counts
*finite* verbs and the leakage comes from clauses headed by participles, infinitives and
relative pronouns.

**One correction to my own earlier phrasing:** the 623 leaked fillers were *counterfactual*
— those sentences used the parse in production. The 24.8% is the **rule's** error rate,
which transfers to the 28,370 case-scoped assertions where the rule actually ran. There was
never a list of 623 bad rows to patch, which is precisely why the whole population had to
be re-run.

### The measurement that decided it

I tried to repair rather than withdraw. The gate was widened from "more than one finite
verb" to "more than one verbal anchor of any kind, and no relative pronoun" — exactly where
the leakage pointed (`acl` 75, `xcomp:result` 56, `xcomp` 34, `advcl` 42, nominal-internal
`nsubj` 106) — plus an agreement-based merge collapsing a modifier onto its argument. All
four gate combinations scored on the same sentences:

| anchor gate | relative gate | precision | recall |
|---|---|--:|--:|
| off | off | 0.5518 | 0.8693 |
| off | on | 0.5668 | 0.8181 |
| on | off | 0.5823 | 0.7251 |
| **on** | **on** | **0.5985** | **0.6860** |

Decomposed, the wrong share moved **24.8% → 24.3%**. That is **0.5 points of precision for
18 points of recall.** Per role, with both gates on:

| role | emitted | wrong |
|---|--:|--:|
| GOAL | 88 | 11.4% |
| SOURCE | 61 | 18.0% |
| INSTRUMENT | 125 | 18.4% |
| PATIENT | 586 | 18.8% |
| BENEFICIARY | 162 | 30.2% |
| AGENT | 541 | 30.9% |
| LOCATION | 138 | 31.2% |

AGENT splits sharply by case: a vocative under a second-person verb is 23% wrong, an
agreeing nominative under a third-person verb is **39.8% wrong** — and the nominative class
is the larger one. **No role reaches an importable standard and there is no threshold at
which this rule is safe to assert.**

### What I did — the third route

Not "prevent what is preventable" (the sweep shows prevention fails) and not "downgrade the
row" (a row carries many assertions; downgrading the row would also downgrade the
defensible predicate layer). Instead, split by **what each claim rests on**:

1. **Role fillers are asserted only where the DCS parse supplies them** — the treebank's own
   `nsubj`/`obj`/`iobj`/`obl:goal`/`obl:source`/`obl:instr`/`obl:loc` labels. No heuristic.
2. **Everywhere else the assertion is predicate-only**: predicate, frame, verb surface and
   verb features, every one read off the verb token itself and none dependent on role scope.
   Each carries `roles_withheld: true` and its reason.
3. **The withdrawn candidates become an explicitly non-importable queue**,
   `role_candidates.jsonl`, `importable: false` on every row, with the measured per-role
   error rates in the manifest. That is what the contract means by a verification queue.
4. **The `:RoleFiller` projection** is `role_fillers.jsonl` — parse-backed only, importable.

### headline_after

| | before | after | change |
|---|--:|--:|---|
| assertions | 30,274 | 30,274 | unchanged — **see the caveat below** |
| **asserted role fillers** | 51,231 | **2,052** | **−96.0%**, all parse-backed |
| agent+predicate+patient triples | 5,219 | **341** | **−93.5%**, all parse-backed |
| assertions carrying `roles_withheld` | 0 | **28,742** | these assert strictly less than before |
| non-importable role candidates | 0 | 32,025 over 15,704 assertions | the verification queue |
| known error in asserted role fillers | 24.8% | **none measured** | the instrument that had one no longer asserts |

**The caveat on the unchanged assertion count, stated plainly because the instruction was
not to preserve it by loosening anything.** Nothing was loosened. The count is identical
because a predicate and a frame are read off the finite verb's own lemma and morphology and
never depended on role scope — the same 23,622 Rigvedic finite verb tokens resolve to the
same 22,192 predicates. What changed is what each assertion *claims*: 28,742 of the 30,274
now assert a predicate and a frame and explicitly withhold roles. If the campaign prefers to
publish "assertions that carry at least one asserted role", that figure is **1,532**, down
from 30,274.

### Per Veda, processed and positive — the figures the campaign publishes

| | RV | SV | YV | AV |
|---|--:|--:|--:|--:|
| **processed** | 10,552 | 1,844 | 1,975 | 5,839 |
| **positive** (≥1 assertion) | 10,150 | 216 | 574 | 3,295 |
| assertions | 22,192 | 372 | 1,543 | 6,167 |
| **asserted role fillers** | **0** | **0** | 387 | 1,665 |
| assertions with roles withheld | 22,192 | 372 | 1,198 | 4,980 |
| triples | 0 | 0 | 56 | 285 |
| non-importable candidates | 28,341 | 0 | 599 | 3,085 |

**Processed and positive counts are unchanged from what the coordinator has already
reported to the owner** — 10,150 of 10,552 Rigvedic passages still carry an assertion, and
that figure needs no correction. **The figure that does move is the second one: three-slot
assertions went 0 → 5,219 and are now 0 → 341.** The owner should be told that directly.
The Rigveda now has a predicate layer and **no** role layer, because it has no parse.

No Samavedic candidate is projected: a candidate that is both case-derived and
cross-Veda-projected would be two unverified steps deep.

### What this costs and what it buys

Costs: the Rigveda loses its role layer entirely, and 96% of role fillers move from asserted
to queued. Buys: every asserted role filler in the artifact is now a label from a
human-validated dependency parse, so there is **no known error rate left to discount**. A
smaller defensible layer, as instructed.

Records: `proofs/adversarial_preflight_case_scoped_roles.json` (the attack),
`proofs/wave3_gate_sweep_and_withdrawal.json` (the repair attempt and the per-role rates).

## Known limitations, stated plainly

1. **1,390 Atharvavedic and 1,191 Yajurvedic mantras have no morphological source.** AVŚ
   kāṇḍa 20 (143 hymns) and 69 of the 72 hymns of kāṇḍa 19; VSM adhyāyas 16–40. This is
   source coverage, measured from the corpus's own file list, not a pipeline failure. A
   further 10 Atharvavedic verses *do* have a source and are the run's only unresolved
   rows: their hymn fell below the skeleton match floor, so no sentence in it was placed.
2. **Three quarters of the non-Rigvedic material has no dependency parse** and is read by
   the same case heuristic as the Rigveda. Typed `MORPHOLOGY_RULE_CASE`, never as treebank
   evidence.
3. **The Rigveda has the weaker instrument.** It has the better *morphology* — manual,
   scholarly, corrected against Grassmann — and no parse at all, while the Atharvaveda and
   Yajurveda get a real one on a quarter of their sentences. The layer's evidential quality
   is therefore *not* ordered the way corpus prestige would suggest, and a product surface
   that says "Rigvedic semantic roles are the best-attested" would be wrong.
4. **The root map is Rigvedic and its reach into DCS is under half.** 4,714 of 10,881
   Atharvavedic and 1,051 of 2,594 Yajurvedic finite verbs get no predicate. The residue is
   itemised per lemma fold in `proofs/dcs_coverage_and_root_map_reach.json`, and this is the
   highest-value follow-on in the domain: `vid`, `i`, `pā` and `dviṣ` alone account for 769
   Atharvavedic and 115 Yajurvedic finite verbs. That is a bounded philological task over a
   named list of about twenty DCS lemma strings, not an acquisition.
5. **Roles are pada- or sentence-scoped, not clause-scoped, and this is now measured.**
   1,115 Rigvedic padas and 2,423 Atharvavedic unparsed sentences hold more than one finite
   verb; those assertions keep their predicate and frame and carry **no** non-agent roles.
   That gate counted only *finite* verbs, and the Wave-3 preflight showed it was not
   enough: 24.8% of case-scoped fillers were attached across a clause boundary or given the
   wrong role, the leakage coming from participles, infinitives and nominal-internal
   subjects the gate could not see. Widening the gate moved it only to 24.3%, so **the
   case-scoped role reading was withdrawn**. Roles are now asserted only from a dependency
   parse, and the Rigveda — which has none — has no role layer.
6. **A predicate edge is not a parse.** The root map says so in its own recommendations,
   point 8, and it is repeated on every `MORPHOLOGY_RULE_CASE` row's `mapping_method`.
7. **`IS_OR_BECOMES` is 2,035 Rigvedic assertions** and is not an action. It is excluded
   from action profiles by the registry's own instruction and must stay excluded.
8. **HEALS is 4 Rigvedic assertions** and CURSES is 22. HEALS exists at all only because two
   sub-floor roots were rescued in the root map. Both must be reported with their counts
   attached, never as bare categories.
9. **The Samavedic 216 are not independently annotated** and are the first rows to
   re-derive if a Sāmavedic annotation ever appears.

## A ruling I need

The 216 Samavedic rows are staged at `mapping_confidence: EXACT`, on the reading that the
field is about how the row's *key* was established and the key is our own, fixed by string
equality. The evidential weakness lives in `evidence_layer`,
`derivation: CROSS_VEDA_TEXT_IDENTITY` and `independently_annotated: false`. If the lead
reads `mapping_confidence` as covering the claim rather than the key, these should be
`PROBABLE` and therefore staged-not-imported. It is a one-line change and the count is 216
rows / 372 assertions.

## Gaps

| gap | effect |
|---|---|
| `GAP-SEMANTICS-001` | `HAS_SEMANTIC_ASSERTION` would reach all four corpora; RV rises 2,542 → 10,150 of 10,552. **Closable.** |
| `GAP-SEMANTICS-003` | three-slot assertions 0 → **341**, all parse-backed. The `:Devata`-only range is **not** closed and cannot be by a staging artifact; the additive proposal is above. **Partial.** |
| `GAP-MORPHOLOGY-002` | a morphological layer reaches AV and YV for the first time, typed distinctly from the Rigveda's manual annotation. Does not reach the Samaveda, and that negative is now evidenced. **Partial.** |
| `GAP-MORPHOLOGY-003` | the Padapāṭha source is located on VedaWeb. The false scope statement still needs correcting in `works.yaml`, which is not my write surface. **Source located.** |
| `GAP-MORPHOLOGY-001` | untouched. The 9,992 isolated `:Lemma` nodes are a separate projection-policy question; this artifact adds no `MENTIONS_LEMMA` edge. |

## Dead ends, named

- **Positional verse assignment inside a DCS hymn.** The base `sent_id` looked like a verse
  id on the first file read and is not: 38 of 519 AVŚ hymns matched, 0 of 15 adhyāyas.
- **UD_Sanskrit-Vedic as a second witness.** It is the treebanked quarter of DCS.
- **VedaWeb for Atharvavedic annotation.** `avs` has no annotation resource; `avp` is the
  wrong śākhā.
- **A blanket de-accenting fold.** Stripping U+0301 everywhere merges `aś-` with `as-` and
  cost 936 Atharvavedic and 576 Yajurvedic verbs before it was caught; stripping the macron
  after a vocalic liquid merges `kr̥-` with `kr̥̄-` and cost another 499 and 51. Both were my
  own bugs, found by reading the abstention list rather than the accepted list.
- **Any agreement or precision figure.** There is no independent witness and no human gold
  set, so none is claimed.

## Reproducibility

`data/staging/semantic_roles/` holds `lib_roles.py`, `clause_scope.py`, `extract_rv.py`,
`extract_dcs.py`, `extract_sv.py` and `build.py`, and emits `rows.jsonl`,
`rejected.jsonl`, `sources.jsonl`, `role_fillers.jsonl` (the `:RoleFiller` projection,
importable) and `role_candidates.jsonl` (the verification queue, `importable: false`). Each
module is SHA-256'd into the manifest's `config`, and
`config_hash` is the digest of that config. The DCS snapshot id is the digest of the sorted
list of the 534 individual blob digests. Every row carries `source_snapshot`,
`algorithm_version`, `config_hash`, `code_commit`, `population`, `processed_count`,
`positive_count` and a compact `evaluation` block.

Validator: `scripts/validate_staging_artifact.py data/staging/semantic_roles --graph` —
**PASS**, 15 checks, every one at 100% evaluation coverage, including
`graph.canonical_key_resolves` and `graph.veda_agrees` over all 14,235 rows and checksums
over all five emitted files. Re-run after the Wave-3 correction.

Neo4j was read-only throughout. `MATCH`/`RETURN` only; no `CREATE`, `MERGE`, `SET` or
`DELETE` was issued.
