# Owner decisions in force

Recorded so a resumed session does not ask again. Each is binding on the campaign and on
Wave 3.

## 1. Soma / Soma Pavamāna — specialized form, separate analytical nodes

**Decision.** Both distinctions carry useful semantics, and `EPITHET_VARIANT_OF` is too
strong for this case. Keep Soma and Soma Pavamāna as separate analytical nodes. Do not
merge them, do not delete the analytical distinction, and do not weaken
`EPITHET_VARIANT_OF` generally.

**Predicate chosen: `SPECIALIZED_FORM_OF`.**

Selected over the owner's alternative `RITUAL_ASPECT_OF` for two reasons. The existing
ontology names relations in the `X_OF` idiom — `EPITHET_VARIANT_OF`, `VARIANT_OF`,
`MEMBER_OF`, `MEMBER_OF_FAMILY` — so `SPECIALIZED_FORM_OF` reads as one of the family
rather than as an import. And it generalises where `RITUAL_ASPECT_OF` would not: the same
relation may later be needed for a specialization that is functional rather than
liturgical, and a predicate named for ritual would then be either misapplied or duplicated.

**Semantics.** `A SPECIALIZED_FORM_OF B` means A is a contextually specialized
manifestation or form of B, and remains separately addressable for corpus analysis.

It must not be read as an orthographic alias, an epithet spelling, a licence to collapse
the nodes, or complete interchangeability in every query. Those readings are what made
`EPITHET_VARIANT_OF` wrong here.

**Scope.** Migrate **only** the Soma Pavamāna → Soma edge, unless independent review finds
another relation with the same semantic problem. The other 10 `EPITHET_VARIANT_OF` pairs
stay as they are: sampled, they are epithets proper — "Agni Jātavedas", "Agni the slayer of
demons", "the self of Agni" — rather than distinct cult forms.

**Not yet applied.** Wave 3 is not authorized, so this is staged as a migration card with
the former edge's provenance preserved, not written to the graph.

## 2. Normalization is a comparison instrument, never identity evidence

**Campaign-wide invariant.** Unicode normalization, accent folding, punctuation folding,
whitespace folding, script transliteration, sandhi-normalized comparison, case folding and
OCR normalization may all **generate candidates**. None of them alone may establish that
two things are the same canonical passage, the same entity, the same recension, a
`VARIANT_OF`, or a text reuse, and none may license a canonical merge.

Canonical identity requires independent evidence: a stable source coordinate, work or
recension identity, a source-local structural address, verified content alignment, or an
explicit source assertion.

**Three states must stay distinct:**

| State | Means |
|---|---|
| `NORMALIZED_EQUIVALENCE` | the strings fold together |
| `CANONICAL_IDENTITY` | they are the same thing, on independent evidence |
| `TEXTUAL_VARIANT` | a real difference in transmission |

**Classification rules.**
- Same canonical source location, difference only in accent or punctuation → may become an
  orthographic or normalization variant.
- Same folded text at **different** coordinates → **not** the same passage merely because
  it folds identically.
- Two different texts that self-reference coordinates → the embedded coordinate strings are
  **not** edition variation. This is the defect that mistyped 134 pairs.
- Transliterated Devanagari-to-Latin matching → candidate generation, not identity proof.

**Regressions.** The Atharvavedic and Yajurvedic inline-self-address defect and the
anusvāra fold defect both become regression tests for this invariant. One consequence is
already recorded as a blocker: correcting the fold in place trips the referent-drift gate,
because `referent.py` computes `comparison_sha256` through it — which is this invariant
appearing from the other side, a normalization change reading as an identity change. See
`FOLD_FIX_BREAKS_REFERENT_IDENTITY` in `data/staging/integration/blockers.json`.

## 3. The four additive schema extensions are approved in principle

Approved subject to each migration card demonstrating all five:

```
ADDITIVE                      = true
DETERMINISTIC_IDENTITY        = true
BACKWARD_COMPATIBLE           = true
ROLLBACK_DEFINED              = true
OLD_PREDICATE_MEANING_CHANGED = false
```

If `OLD_PREDICATE_MEANING_CHANGED` is true, that migration is **not** pre-approved and
returns to the owner.

`:RoleFiller` is explicitly included, because the existing schema cannot represent the
majority of role fillers without semantic distortion — measured at 93.1% unrepresentable.

### The `:RoleFiller` model

A `:RoleFiller` is a **semantic-role occurrence in an assertion**, not a duplicate of a
canonical entity. Where it corresponds to a known canonical thing, connect it:

```
(:RoleFiller)-[:REFERS_TO]->(:Devata | :Object | :Substance | :Plant | :Place | :Concept | …)
```

It exists because the role occurrence and the entity referred to are not the same graph
object. Do not duplicate canonical entities to stand in for fillers.

Each filler preserves: role, passage, predicate or assertion, surface evidence, referent
confidence, source method.

## 4. Human gold is not required where source adjudication is the strongest available

**Correction to a lead error.** The lead reported that the campaign could not reach
`COMPLETE` because no bespoke human gold set exists. That was wrong, and it conflated two
different things.

The original contract allows an `INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET` where human
annotation is unavailable. So `HUMAN_GOLD_NOT_AVAILABLE` is a **documented evaluation
limitation**, not an open implementation gap, and it does not by itself prevent a
`COMPLETE` decision.

Agent 16 must still search for and use real human annotation wherever it exists — and it
did, using a published human treebank for three of the four layers it scored. A
source-adjudicated or model-adjudicated set is never to be called human gold.

## 5. Samaveda morphology — the annotation source is absent, the analysis is not

**Correction to the same lead error.** Three independent searches found no published
Samavedic morphological annotation. That is an external annotation-source gap. It does not
prevent the implementation gap from closing.

All 1,844 Samavedic mantras are to be processed through the campaign's explicit
model-assisted or deterministic morphology pipeline, with provenance marked. The final
distinction to report:

```
PUBLISHED_HUMAN_ANNOTATION = unavailable
MORPHOLOGICAL_ANALYSIS     = processed
```

Lack of scholarly annotation is not inability to build an analytical layer.

## 6. Samaveda audio — do not declare blocked until LOAR is fully classified

Kauthuma Ārcika exact verse audio stands at 0 of 1,844. Do not fabricate coverage. Continue
LOAR classification, the IGNCA and Vedic archive search, and the public recitation search.

If exhaustive search finds no authentic exact or segmentable Kauthuma Ārcika source, the
final state may be `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE` — **provided** the registry's
addressing and source-search proof requirements are met. That is not an implementation gap.
But it may not be declared until LOAR and the remaining candidates are fully classified.

## 7. IGNCA Mādhyandina — reachable public material may be used

If the recordings are publicly reachable without authentication or any technical
access-control bypass, they may be used as `REMOTE_DIRECT` or another
provenance-preserving external playback mode. Redistribution licensing analysis is not a
blocker for this private project.

No bypass of login, authentication, DRM, CAPTCHA or a restricted private endpoint. If
*access* itself requires affirmative permission rather than merely permission to republish,
retain `NEEDS_OWNER_PERMISSION_REQUEST` until granted.

## 8. The listening queue stays honest

The 1,021-row audible-review queue is real and the gate is not to be weakened. Automated
text comparison, metadata review, waveform checks and ASR are **none of them** listening
review.

States: `NEEDS_AUDIBLE_REVIEW` · `AUDIBLY_VERIFIED` · `AUDIBLY_REJECTED`.

No new fragile audio enters the canonical layer as fully verified until the required
audible review is complete. The engineering campaign proceeds around this queue.

## 9. Registry items do not close yet

80 gaps, 0 closed, and that is the expected state before Wave 3 readback. A gap closes only
after canonical import or derived-layer build, readback, its closure test, and product or
API propagation where applicable. Staged work is not closed work.

## 10. The success criterion

`OPEN_IMPLEMENTATION_GAPS` must reach 0. External blockers may remain **only when proven**.

The distinction:

- **Implementation gap** — something we could build, process or import and did not.
- **External source blocker** — required external evidence genuinely does not exist, or
  cannot be accessed, after exhaustive documented search.

The campaign is not impossible because external resources are absent.

---

# Second owner round, 2026-09-15

The owner's blockers are resolved. These supersede nothing above; they settle the
questions the first round left open, and they bind Wave 3.

## 11. Folding is not identity — and the fold blocker is decided by that

**Decision.** Normalization, accent, punctuation, whitespace and case folding, script
transliteration, sandhi-normalized comparison, OCR normalization and generic folded-label
equality may establish `NORMALIZED_SURFACE_MATCH` or produce an `IDENTITY_CANDIDATE`.
None of them establishes `SAME_CANONICAL_ENTITY`, `SAME_CANONICAL_PASSAGE`, `VARIANT_OF`,
`TEXT_REUSE` or a canonical merge. **Do not equate them.**

**What that decided.** `FOLD_FIX_BREAKS_REFERENT_IDENTITY` is the same invariant seen from
the other side: the fold sat *inside* the identity contract, so correcting a comparison was
indistinguishable from a referent moving. Resolved by option B — the comparison surfaces
get their own fold and the identity fold is untouched.

**Applied.** `fold_transcription_cross_script` and `ComparisonForm.CROSS_SCRIPT_COMPARISON`,
consumed only by `enrich.surfaces.build_surfaces`. Verified: all 3,819 released referent
digests reproduce byte for byte, including the five Yajurvedic keys the in-place fix would
have drifted; the generated lexical layer still rebuilds byte-identical; 0 records change
on `SEARCH_NORMALIZED`.

**What enumerating the residue found that the staged patch had not.** Three further arrival
forms — U+1CEC, U+A8F7, and the ASCII tilde the transliterator makes of U+0901 — plus four
editorial marks surviving onto the comparison surface, and one form that is deliberately
**not** folded: U+F15C, a private-use code point in the stored text of 20 unaccented
Vājasaneyi records, sitting where that layer elsewhere writes an anusvāra. Reading it as one
is a transcription judgement rather than a normalization, so it is registered as a source
defect and left alone.

The patch's own two proposed rules turned out redundant: each component already folds to the
sentinel, and the run collapse merges them.

**Re-recorded deliberately.** The cross-Veda identity baseline moves 1,538 → 1,735:
`EXACT_PARALLEL_OF` +45 and `VARIANT_OF` +152, across all six pairs.

**Deferred as a choice, not an omission.** Option A — versioning the comparison digest by the
normalization that produced it — remains the more correct end state and waits for the next
deliberate revision of the identity contract.

## 12. `scope_type` comes from the evidence grain; M6 is split

**Decision.** There is no global default `scope_type`. It is an evidence property, derived
from the actual subject grain, using the narrowest truthful closed-enum scope each population
supports. A heterogeneous M6 must be split into homogeneous import populations.

**What the card got wrong.** It asked which readers could be allowed to break. `scope_type`
is on **0 nodes and 0 relationships** of the live graph, so there is no reader to break, and
`ADDITIVE = false` / `BACKWARD_COMPATIBLE = false` were recorded against a population that
does not exist. The schema already held both vocabularies as separate closed enums —
`AudioScope` with its `SCOPE_TO_ENTITY_TYPES` grain contract, and `ScopeType` for assertion
scope — so no vocabulary had to be invented and no winner had to be picked.

| Population | Property | `scope_type` | Enum | Rows | Grain asserted |
|---|---|---|---|--:|---|
| `AUDIO_RECORD_AT_MANTRA_SCOPE` | `audio_scope_type` | `MANTRA` | `AudioScope` | 954 | every subject is `entity_type=MANTRA` |
| `GANA_PERFORMANCE_AT_COLLECTION_SCOPE` | `audio_scope_type` | `COLLECTION` | `AudioScope` | 3 | every subject is `entity_type=STRUCTURAL_CONTAINER` |
| `ATTRIBUTION_ASSERTION_AT_SINGLE_MANTRA_SCOPE` | `assertion_scope_type` | `SINGLE_MANTRA` | `ScopeType` | 466 | every subject is `entity_type=MANTRA`, and all 466 independently carry `asserted_granularity=VERSE` |

**Defect found and fixed.** The three gāna rows were staged `STRUCTURAL_CONTAINER`, which is
a graph `entity_type` and **not a member of `AudioScope` at all** — one axis's value cast into
the other's enum. `AudioScope.COLLECTION` is the enum's own value for a named Samavedic
collection, and all three keys are CHANDA or UTTARA containers.

The split is a total partition of the 1,423 scope-bearing rows, and M6 now passes all five
flags: nothing writes a property called `scope_type`, so no predicate changes meaning.

Validator: `scripts/wave3_scope_grain_repair.py` → `HOMOGENEOUS_AND_ON_GRAIN`.

## 13. SOMA-PRESSING stays; its weak aliases lose assertion authority

**Decision.** Keep `VG:CONCEPT:SOMA-PRESSING` as a canonical ritual object. Its weak lexical
aliases may not establish identity alone. Retain them for search, candidate generation, audit
and manual review; they must not create `MENTIONS_ENTITY`, `ABOUT_CONCEPT` or ritual identity
by themselves. Re-evaluate every existing edge whose sole evidence is a retired alias.

**The criterion is measured, not editorial.** `h2_verdict = AMBIGUOUS_SURFACE` in the quality
artifact's per-alias soundness proof: the alias's dominant human lemma holds under 80% of its
occurrences in a published human treebank.

| Alias | Treebank | Dominant share | Status |
|---|---|--:|---|
| `sute` | su 6 / suta 6 | 0.500 | retired — named by the owner |
| `suteṣu` | su 2 / suta 2 | 0.500 | retired — same split, same formation |
| `sutāsaḥ` | su 9 / suta 4 | 0.692 | retired — named by the owner |

`suteṣu` is not one of the owner's two examples and is retired anyway, because the same
measurement selects it at the same value as `sute`; retiring one and keeping the other would
be arbitrary. 14 trigger aliases survive.

**New registry mechanism.** `non_triggering_aliases` in `data/registry/concepts.yaml`, scoped
per concept — unlike `ambiguous_aliases`, which is contested between concepts and withdrawn
from all of them. A form may be unsound for one concept and perfectly sound elsewhere, so
withdrawing it globally would destroy evidence that is not in question.

**Edges re-evaluated across both layers.** `MENTIONS_ENTITY` reads its dependence off
`matched_aliases`; `ABOUT_CONCEPT` carries none, and its stored evidence quote is a window
round the match rather than the whole verse, so that layer was re-derived over all 20,210
mantras with and without the three forms.

- `MENTIONS_ENTITY`: 117 retire, 12 keep with the alias dropped, 527 untouched.
- `ABOUT_CONCEPT`: 108 retire, 9 narrow from `english+sanskrit` to `english`, 5 newly attested.
- Every retired edge rests solely on a retired alias: 0 passages keep the concept on other
  evidence.

**One consequence held back for its own decision.** `assign_concepts` caps a passage at four
concepts and breaks ties on each concept's **corpus-wide** attestation count, so withdrawing
three aliases reshuffles the cap on passages containing no soma alias at all: 5 assertions
lost and 24 gained across 17 other concepts, net −84 over the layer. Deterministic and
reproducible, and outside the decision the owner took, so it is reported rather than folded
into it.

**The five senses are held apart**, verified: `SOMA-DRINK`, `SOMA-PRESSING`,
`GRAHA-SOMA-DRAWING`, `DEVATA:SOMAH` and `DEVATA:PAVAMANAH-SOMAH`, with no shared Sanskrit
alias between any two.

**Reported, not applied.** The same criterion selects 24 further aliases across 18 other
entities. The owner's decision names this concept, and withdrawing an alias has a measured
blast radius beyond its own concept.

## 14. The audible queue stays mandatory and blocks only audio

**Decision.** The 1,021 rows stay `WITHHELD_PENDING_AUDIBLE_REVIEW`. No automated text or
metadata check may relabel them. Audio does **not** block the non-audio Wave 3 domains.
Allowed final states: `AUDIBLY_VERIFIED`, `AUDIBLY_REJECTED`, `AUDIBLE_REVIEW_UNCERTAIN`.

**Built.** `scripts/audio_review_harness.py`, a local resumable harness. Per item it shows
audio playback, canonical citation, canonical Sanskrit, source citation and coordinate,
mapping method, the prior automated checks and what to listen for; it records the decision,
the reviewer, `reviewed_at`, notes and the seconds actually heard.

Three refusals are enforced at the endpoint rather than asked of the reviewer, and each is
tested: `AUDIBLY_VERIFIED` and `AUDIBLY_REJECTED` are refused when nothing played, a verdict
needs a named reviewer, and a verdict outside the three is a 400. `AUDIBLE_REVIEW_UNCERTAIN`
is allowed with no audio, because that is the honest answer when a recording will not play —
a queue that makes uncertainty inconvenient collects false certainty.

The decision log is append-only and fsynced before the response returns; the queue is a
projection of it, so a changed mind leaves both judgements on the record.

**Still 0 of 1,021 reviewed.** A hand-probe of the gates left one self-test decision in the
log; it was removed and the probes became tests against a temporary queue, because a gate
probe that moves the figure it is probing is the small dishonesty this campaign keeps finding.

## 15. Semantic resemblance: keep the chosen layer, re-derive after import

**Decision.** Do not replace the chosen predicate because the lexical control scored higher.
The predicate stays defined independently of the control. Preserve the reported limitations —
the pool-recall bound, the within-pool metric distinction, the raw-encoder threshold collapse,
the adjudicator disagreement around `SHARED_PHRASING_ONLY`, and the refused tiers. Do not
market the layer beyond its measured evaluation. Re-derive from the post-import snapshot.

**Consequence for Wave 3.** `semantic_resemblance` depends on `translation`, `semantic_roles`,
`attribution` and `formula`; two of those import in this wave, so its inputs move. Importing
its current artifact would land a layer computed over superseded inputs. It is a **step-5
dependent re-derivation, not a step-4 addition** — 19,088 rows withheld for that settled
reason rather than for a pending question.

**Tier B is REFUSED, not blocked.** Its RV–AV guard needs a deity vocabulary bridge that does
not exist, which is now a measured limitation of the layer rather than an open question.

## 16. `CROSS_VEDA_DEVATA_IDENTITY_BRIDGE` is its own implementation gap

**Decision.** Treat the zero intersection as a separate implementation gap. Bridge through
canonical Devatā identity, never through display labels. Where an AV ascription cannot
deterministically resolve, retain the unresolved form. Do not guess.

**Verified and sized.** `HAS_DEVATA` carries 210 distinct display labels over 10,558 edges;
`HAS_DEVATA_ASCRIPTION` carries 324 over 5,385. They share **0**. The zero is a category
difference, not a coverage accident: one side is a deity's name in English, the other a
Sanskrit adjective meaning *having X as its deity*.

A deterministic parse resolves **8 of 324** ascriptions (2.5%), and 9 of 569 occurrences
(1.6%). The residue: 167 carry no recognised deity-adjective suffix, 85 strip to a stem
matching no canonical Devatā, 61 are compounds naming two ascriptions, 2 are subject
descriptors — Whitney's apparatus puts a hymn's subject in the deity slot — and 1 names a
plurality.

Registered as `GAP-CROSS-VEDA-DEVATA-IDENTITY-BRIDGE-001`, `causation_status: MEASURED`,
`source_availability: HELD_LOCALLY`. Buildable work, blocked on neither a source nor an owner.

## 17. `DEFECT_FOUND_AND_FIXED` counts as a completed adversarial gate

**Verified, and already fixed.** `scripts/wave3_eligibility_ledger.py` accepts it in both the
eligibility test and the missing-gate computation. `ritual` and `scholarship` are ELIGIBLE on
it, and each preserves its original defect, the fix, the restage and the post-fix validator
result. No corrected domain is sent through its investigation again.

---

# Owner round three — Wave 3 closed, RitualStep identity, attribution

## 18. Corpus deletions ratified, and now enumerated

**Applied.** The owner ratified the three batches and required the exact IDs and reason for
each to reach the audit trail. They were counted in prose and never listed.

`scripts/corpus_deletion_audit.py` reconstructs them rather than remembering them: a key is
listed because the current plan refuses it **and** the graph does not hold it, both halves
recomputed. Attribution to a batch replays both versions of the reachability rule instead of
inferring from a flag, and the replay reproduces the ratified split exactly — the script
exits non-zero if it ever stops doing so.

| batch | n | reason |
|---|---:|---|
| `BATCH_1_EVIDENCE_NOT_IMPORTED` | 12 | attested only in a Brāhmaṇa or Śrautasūtra, and that evidence is declared not-imported |
| `BATCH_2_ATTESTATION_WITHOUT_LOCATOR` | 2 | `samhita_attested` with no example recorded; `roles.jsonl` has no such field at all |
| `BATCH_3_REACHABLE_ONLY_VIA_A_REFUSED_EDGE` | 27 | named only by a rite edge staged `PROBABLE` |

Full key lists: `data/staging/integration/corpus_deletion_audit.json`. Recoverable from
`wave3-pre-import-20260915T155144`. **No further deletions were made this round.**

An earlier version of this audit split the 41 as 32/2/7 by using `samhita_attested` as a
proxy for which rule applied. That was recorded, found wrong, and replaced with the replay.

## 19. `:RitualStep` identity — the grain was measured, not chosen

**Applied as M7.** The owner barred exposing `step_key` merely to make traversal work and
required the grain to be determined from the artifact. Measured over 3,123 importable rows:

| grain | distinct | values covering rows that **disagree** |
|---|---:|---:|
| `SOURCE_OCCURRENCE` | 2,767 | 308 |
| `RITE_SPECIFIC_OCCURRENCE` | 3,122 | 1 |
| `POSITION_BASED` | 1,137 | 680 |

Source-occurrence would merge 308 identities standing for different claims, because one sutra
is cited for several rites. Position-based fails outright — `step_position` restarts inside
every work. **The grain is rite-specific occurrence**, and the `step_key` Wave 3 already
staged is exactly that: rite + work + printed source coordinate, with a canonical URN and
`uuid5(7c8cde94-…, urn)` verified byte-identical for all 3,123 rows.

So no identity was invented. M7 writes one property, `display_type = "RITUAL_STEP"`, and the
traversal refusal — whose stated reason was that the nodes had no product type — is retired.
`HAS_STEP` is untouched and still means the Samhita's own numbering.

`HAS_RITUAL_STEP` is traversable but **not** a path predicate: a path hopping rite → step →
rite would assert a relation between two rites whose only connection is that one sutra
collection mentions both.

## 20. Attribution — the census imported, Whitney withheld

**Gates B and C both run, nothing inherited from the domain's own report.**

The 23,003 rows are two populations sharing one file, and averaging them would have hidden
both findings:

- **Census, 22,537 rows.** Per-passage records of the *state* of rishi/devata/chandas
  attribution. Not assertions about the text — an edge saying "this mantra has no recorded
  seer" is a fact about the record. Gate C checked all 67,611 state assertions against the
  edges that actually exist, stratified 38 ways: **0 contradictions.** Imported as three
  properties per passage, 0 nodes and 0 edges.
- **Whitney index, 466 rows.** Genuine verse-level source assertions, and every one carries
  `entity_resolution_method = VERBATIM_SOURCE_STRING_NOT_RESOLVED`. The object is a printed
  Sanskrit string that resolves to no node. **Withheld**, classified
  `RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT`, registered as
  `GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001`. Resolving them by normalized string
  equality is exactly what the owner's rules forbid.

What the import bought: this graph can now distinguish a source that was consulted and says
nothing (`ASSESSED_SOURCE_ABSENT`) from one nobody has opened (`NEVER_ASSESSED`) from a
container asked a question only a verse can answer (`NOT_APPLICABLE_AT_THIS_GRANULARITY`).
Before, all three read as one silence and every absence could be taken for a verified zero.

## 21. Two gates that could not fail

Recorded because both were passing while measuring nothing.

**The scorecard's undeclared-type gate.** `declared = ONTOLOGY | everything in the graph`,
then "which graph types are not in `declared`?" — structurally empty. It reported 0 for a
whole wave while eleven Wave 3 predicates went unclassified. It now measures against the API's
product contract, which a live test holds complete.

**The dependency invalidation's one-way status.** Staleness was computed from the wave stamps,
which never come off, so every consumer read `STALE_INPUT` for ever and a rebuild could not be
expressed. `scripts/rebuild_ledger.py` adds the missing half: `CURRENT` means a recorded
rebuild whose input hash still equals the current one, scoped to the labels and predicates
that consumer declares it reads.

## 22. What this round did not do

- **Semantic resemblance is not re-derived.** The staged artifact is pre-Wave-3
  `hybrid-v2`, and section 8 bars importing an old score artifact. Zero rows imported;
  status `BLOCKED`.
- **The Ask benchmark is not re-graded.** Retrieval reads the graph live and its 280 contract
  tests pass; only the graded run is stale, and re-grading burns a daily quota.
- **No audible reviews.** Still 0 of 1,021, and still a parallel track.
- **Wave 4 not begun.**

---

# Owner round four — integrity gates, labels, Whitney, semantics

## 23. Both vacuous gates replaced, and both can now fail

**The relationship declaration gate, third version.** The reason each earlier one was wrong
is now in the code beside it:

| version | reference set | why it could not fail |
|---|---|---|
| v1 | `ontology ∪ every type in the graph` | membership is tautological |
| v2 | the API's traversable/refused lists | a product decision, not a schema declaration |
| v3 | `ontology.all_declared_relationship_types()` | composes layer authorities; the graph is not an input |

Measured before the repair: **18 populated relationship types declared by nothing.** Ten
were this campaign's. Eight were pre-existing corpus and traditional-metadata predicates
carrying 138,143 edges, whose constants sat in the ontology under the comment *"listed so the
closed vocabulary is complete"* and then reached no declared set — because
`RELATIONSHIP_SIGNATURES` is asserted equal to `DOMAIN_RELATIONSHIP_TYPES` and these have no
V2 signature. The closed vocabulary was never closed.

Declared additively as `CORPUS_RELATIONSHIP_TYPES` (8) and `CAMPAIGN_RELATIONSHIP_TYPES`
(10), each with an endpoint signature **measured against the live graph** rather than
intended. Declared 90 · graph populated 76 · undeclared **0** · declared-but-unused 14 (all
architecture) · system exceptions **0**, declared explicitly so adding one is a visible act.

The signature gate is widened with them: it iterated `RELATIONSHIP_SIGNATURES` only, so those
18 predicates — **141,264 edges** — had their endpoints checked by nothing at all.

**The dependency staleness gate.** Round three's per-consumer hashes were the right shape and
too weak in three ways, all fixed: counts are unchanged by a swap of equal size, so labels
now digest sorted identity keys and predicates sorted endpoint pairs; declared **file** inputs
were invisible; the **builder's** own source is now an input. `built_at` is metadata and
`classify()` is grepped by a test for `built_at`, `wave3_` and `datetime.now`.

40 adversarial and transition tests. Including one that reconstructs the original tautology
and demonstrates it reports nothing for the very input the repaired gate catches.

## 24. The six labels, and a leak that was live

All six were declared by no authoritative source, and the consequence was measured:
**`frontend/.world/world.raw.json` held 2,568 `:QualityVerdict` nodes** — this repository's
assessment of its own passages — as the **fourth-largest type in the public world**, ahead of
`:Rishi`. "Public" is one clause, `NOT n:Internal`, and nothing had marked them.
`:RoleFiller` and `:DeityCommunity` escaped only because they carry no id key and the export
drops what it cannot name, which is luck rather than a boundary.

| label | n | disposition |
|---|---:|---|
| `Scholar` · `ScholarlyWork` · `ScholarlyDisagreement` | 17 · 17 · 113 | **canonical product-visible** |
| `QualityVerdict` | 2,568 | **internal** — a fact about the record |
| `RoleFiller` | 2,052 | **internal** — wiring, no `entity_key` |
| `DeityCommunity` | 12 | **internal** — an analytic partition with its refusal attached |

M8 marked 4,632 nodes. Public nodes 44,324 → 39,692; total nodes, relationships and the four
corpus totals unchanged. Re-exported and verified: **0 of each** in the world file.

Demoting the scholarship classes would have emptied the difference set faster and hidden real
knowledge content. Final undeclared public labels: **0**, with an empty exception list.

## 25. Whitney 466 — withheld, and not for want of evidence

Four channels attempted; three refused with stated reasons (surface/normalized equality;
verse-local context, because the rows are *exceptions* to their hymn and would resolve to the
value the source contradicts; `rv_registry_name_match`, which the registry's own header
declares non-evidential). The permitted channel — the AV registries' `source_variants`,
generated from the same Whitney index — **works**: 405 of 477 proposals resolve, 0 ambiguous,
0 findings against any individual resolution.

**And nothing is imported, because the adversarial pass was checking the wrong object.** Of
541 AV_WHITNEY `:Chandas` entities, a number are unsegmented fragments of Whitney's bracket
carrying a deity, a metre and a per-verse exception in one string —
`'āindryas. ānuṣṭubham: 2. 3-av. 6-p. jagatī'`. Three tests were written to bound the share
and they disagree: **17, 28, 39**. That disagreement is the finding: separating a deity
adjective from a metre name inside these strings is philological adjudication, which may not
act as identity evidence, so a partial import cannot be made safe.

A verse whose recorded metre is a string containing a deity name is worse than a verse with no
verse-level metre. All 466 stay `RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT`; the graph is not
mutated.

**A defect found in data that was already canonical:** 33 `HAS_CHANDAS` edges point at such
fragments today. `GAP-AV-CHANDOMETRE-SEGMENTATION-001`. Not repaired — re-segmenting a
canonical vocabulary re-identifies its entities, which is an owner decision.

## 26. Semantic resemblance — outcome C, measured

**0 assertions imported.** Three reasons, none of them a shrug:

1. The prior artifact declares a 108,779-node graph snapshot; this one holds 116,838. Not
   hash-identical, which was the stated condition for trusting an old pool or score.
2. No semantic representation is computable here — no `onnxruntime`, `transformers`,
   `sentence_transformers` or `.onnx` file. A representation that cannot be computed cannot be
   shown to add value over a control.
3. The control was re-implemented and measured on current canonical inputs: **AUC 0.754**
   over 279 adjudicated pairs (dev 0.774, test 0.736), character 4-grams over accent-stripped
   Sanskrit, no model and no translation channel.

The control does **not** reproduce the prior `C_LEXICAL_CHAR4` — 6 of 370 exact, 292 within
0.05, and the unaccented text gives 7 and 281, so the text role is not the difference. I
expected reproduction and did not get it; the carry-over argument is withdrawn and the fresh
AUC is the baseline instead.

`SHARED_PHRASING_ONLY` stays withheld on **7** adjudicated labels of 486. Seven cannot
establish a boundary. The gold labels are LLM-adjudicated with 162 of 486 left
`UNADJUDICATED_QUOTA_EXHAUSTED`, and are not reported as a human gold standard.
