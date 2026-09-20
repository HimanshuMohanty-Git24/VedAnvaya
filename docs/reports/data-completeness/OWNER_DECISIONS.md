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

## 27. M9 — the 33 malformed metre assertions, withdrawn under authorisation

**Applied.** The correction stops at the demonstrable 33 because the criterion is Whitney's
own notation, not a reading of Sanskrit: `:` separates his hymn statement from its per-verse
exceptions and a bare `N.` is a verse number, and neither can occur inside a metre *name*.
Three heuristics for the wider population gave **17, 28, 39**, and an unbounded criterion
cannot authorise a deletion.

33 assertions · 28 entities · 33 passages · `HAS_CHANDAS` 16,331 → 16,298 · 0 nodes touched ·
`:Chandas` population 575 unchanged · core corpus exact.

**17 passages keep a well-formed metre edge; 16 are left with none.** Replacements created:
**0**, measured — every metre assertion for these passages traces to the same source whose
segmentation is the defect, so no independent evidence exists, and reading the metre out of
the mixed string was barred. On `K03:S003:V005` it would also have been wrong: the `6.` in
`'6. anuṣṭubh'` addresses verse 6 while the edge sat on verse 5.

The literal and its provenance move onto the passage **before** the edge is deleted, in that
order inside one transaction — if it fails between them the assertion survives, which is the
safer half to hold. All 33 affected IDs, literals, scopes and outcomes are in the gap
registry.

**My own readback could not fail, and it is recorded rather than quietly fixed.** Its first
version rebuilt its expectation by querying the graph for the malformed edges, found none
after the withdrawal, and printed `READBACK_CLEAN` having compared 0 against 0. That is the
vacuous-gate defect of §23 inside the tool built to catch it. The expectation now comes from
the executed receipt and it refuses to report a verdict without one.

**The gap stays open.** The registry *builder* is unchanged, so re-running
`build_anukramani_knowledge_layer.py` would recreate the same fragments.

## 28. Ask — blocked by the daily allowance, not faked

A fresh commit-keyed run at `b98d988` from Q1 reached **19 of 60** and stopped at Q20 with
`LLMRateLimitError: the daily allowance is exhausted; waiting will not clear it`. Only
OpenRouter is credentialed — Gemini and Anthropic providers exist in code without keys — and
switching model would produce a different grade rather than a resumption.

The earlier 31/60 run is **diagnostic only and is not combined**, per the instruction.
`ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA` is recorded in the dependency ledger with the
exact error. **`misleading = 0` is not claimed.**

Investigating the uncited answers found a real product defect: the citation extractor did not
recognise round parentheses, so Q20's `(E11)`-cited answer was scored uncited and graded
`INSUFFICIENT_EVIDENCE`. Fixed, with a test that ordinary prose parentheses still yield no
citation. The other two uncited answers are a truncated generation and a reasoning-preamble
leak — model-side, already flagged, not hidden.

# Wave 4 — independent adversarial QA, and what it found about the registry

Full report: [`WAVE4_ADVERSARIAL_QA.md`](WAVE4_ADVERSARIAL_QA.md). Verdict
`VEDANVAYA_DATA_COMPLETENESS_NOT_COMPLETE`, `RELEASE_CANDIDATE = NO`.

## 29. The registry had no closed state, and four decisions are what stand in the way

§9 of this ledger says *"Registry items do not close yet."* Wave 4 discovered that this was
not a policy being followed but a structural fact: `data/gap_registry.json` had **no closure
vocabulary and no field to hold one**. 84 of 85 entries read `OPEN`, 67 carried
`causation_status: HYPOTHESIS_NOT_YET_MEASURED` with all 14 addressing diagnostics `NOT_RUN`,
and `resolution` and `addressing_status` were `None` on all 85. Nothing in that file could ever
have been complete, so the campaign could not have reported completion from it.

Every entry now terminates in exactly one status: **37** data-completeness closures, **8**
separately tracked execution blockers, **40** `STILL_IMPLEMENTATION_FIXABLE`.

**The five blockers that are not source limits.** `GAP-TRANSLATION-002` records *"Closed via
the Wayback Machine, 944 of 961."* The graph holds 4,878 of 5,839 Atharvavedic translations —
exactly the pre-closure figure. All 2,254 accepted rows in `data/staging/translation/rows.jsonl`
target mantras that exist and **none carries a translation**; 1,242 are Samavedic, against an
entry recording the Samaveda as source-blocked, and they are keyed to this corpus's own
canonical keys. Acquired, staged, never imported, recorded as closed.

The gate is `OWNER_DECISION_A_RV_SPAN` + `OWNER_DECISION_C_FORCED_ADDRESSES` for translation
and `OWNER_DECISION_E_AUDIO_GATE` for audio and Samaveda music. `wave3_eligibility.json` has
Gate B `UNKNOWN` and Gate C `NOT_RUN` for all four of those domains, against a stated
eligibility rule of A and B and C all PASS — so the decision needs those gates run first, and
running them is the next substantive piece of work on this project.

Recorded `BLOCKED_OWNER_DECISION_REQUIRED`, counted apart from the closures and never as one.
Two guards stop the cheap alternative: `CLOSED_SCOPE_DECISION` requires a citation naming where
the decision is written down, and `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE` requires all five
fields §L of the brief specified. Either missing and the entry is downgraded.

## 30. Eleven generators were wrong, and the gates that should have caught them

The brief said fix generators, not canonical symptoms. Eleven were fixed at source; the full
table is in §C of the report. Three are worth naming here because of what they say about the
gates:

**`GAP-AV-CHANDOMETRE-SEGMENTATION-001` is closed.** The criterion stays bounded by Whitney's
own notation — a colon separates a statement from its per-verse exceptions, a bare `N. ` is a
verse address — and 39 tests pin 19 malformed strings as refused **and 16 real metre names
carrying `3-av.`/`6-p.` qualifiers as surviving**, which is what keeps the fix from becoming
the 17/28/39 heuristics that were barred. No entity was re-keyed, merged or renamed; the 28
malformed identities were marked `:Internal` and keep their literals. The builder's
import-time `sys.stdout` swap made it unimportable by pytest, which is **why** its own
documented residual shipped, and that is fixed too.

**M10's fix did not reach the reader, and nothing noticed.** The graph was corrected, the
export dropped the 28, and `frontend/public/world/world.labels.json` still carried all 28.
Both world consumers had declared the same *intermediate* as their output, so the Lab stage
was judged on a file its own build never touches; `build-world.mjs` joined the constellation
partition **by position** with no length check, reading 35,370 assignments onto 35,648 nodes;
and `world.predicates.json` was in no consumer's hash.

**A declaration of emptiness is a claim about the graph, and nothing checked it.**
`SHARES_FORMULA_WITH` was declared deliberately unpopulated — *"materialising it would add
87,296 edges"* — and Wave 3 materialised 6,148 on a criterion the reasoning had not
considered. The ontology reference published the false claim, and the same document reported 39
live predicates as undeclared because it read one declaration slice. Both fixed; a new
`falsely_declared_unpopulated` gate reads both maps.

## 31. Four of my own errors, and the checks that caught them

Recorded because the pattern is one rule. A transformation count declared 531 against a
measured 4,368; an unreviewed-assertion count declared 4,865 against a measured 0 because the
property is `review_state` not `review_status`; a reproducibility harness classifying its own
registry audit `DEFECTIVE_REGENERATION` because that script's exit code is a *verdict*; and a
boundary sample reporting 20 valid `TEXTUAL_MENTION` edges as vocabulary violations because I
typed the vocabulary out by hand instead of reading `AttributionPrecision`.

The first two were caught **because the ruling was declared before the measurement**. The
fourth is the same shape as casting a property into the wrong enum and reporting 44,778 edges
as `UNKNOWN`. **Read the declaration; never restate it.**

## 32. Audio: still 0 of 1,021 heard, and the harness now proves its own refusals

Nothing in this wave played audio and nothing simulated it. §14 stands.

The harness's refusals were tested against the **live server** on a loopback port rather than
read from its docstring: unknown verdict, anonymous verdict, `AUDIBLY_VERIFIED` with nothing
played, and an unknown `review_id` all return 400 — and the control matters as much, because
`AUDIBLE_REVIEW_UNCERTAIN` with nothing played returns 200. If every verdict were refused the
four refusals would prove nothing. Run against a synthetic `review_id` in a sandbox; the real
queue still holds 0 verdicts and the real decision log still does not exist.

A generator fix: **804 of 1,021 rows named no source**, because the builder read
`payload.source_name` and the staged payloads do not carry that field. A reviewer was handed a
media URL and left to infer whose recording it is, on the one surface whose entire purpose is a
human judgement. Now 0 unnamed, each row also carrying licence and attribution.

A **100-row seeded owner sample** is at `data/staging/wave4/audio_owner_sample_manifest.json`,
stratified proportionally with a floor of one so the 6-row Samavedic container stratum
survives. Every row is `NEEDS_AUDIBLE_REVIEW` and the manifest has no verdict field at all.

## 33. What Wave 4 did not do

It did not build the forty implementation-fixable layers, and it did not relabel them. It did
not import the staged translation or audio material, because that is decision A, C and E and
not mine. It did not re-key, merge or mass-migrate any entity. It did not run Gate B or Gate C
for the four blocked domains — those are a fresh adversarial pass per domain, not a
by-product of this one. And it did not claim `misleading = 0`: see §L1 of the report for the
formal Ask grade and its status.

# Owner round five — Release Blocker Closure R3

Two decisions the registry had already asked for by name. The R1 hostile pass left
`GAP-SEMANTICS-004` closed on a citation that pointed at itself, and wrote down what would fix
it: *"The owner should write it into OWNER_DECISIONS.md, at which point the citation becomes
independent of this file."* And R2 left `GAP-ENTITY_COVERAGE-008` open on a measure that asks
two intentionally different predicates to agree. Both are settled here.

## 34. OWNER_DECISION_SEMANTICS_004_STRATUM_MAP — no unattributed stratum map

Recorded verbatim, as the owner gave it:

> VedAnvaya SHALL NOT ingest or publish an unattributed historical/chronological stratum map
> for Vedic passages.
>
> A stratum assignment is an interpretive scholarly claim and requires:
>
>     a named scholarly source
>     an identifiable work
>     attributable methodology
>     source-local citation
>     provenance to the specific assignment
>
> The existence of a named asserter alone is insufficient.
>
> No generic, synthesized, model-generated, consensus-looking, or unattributed stratum map may
> be created merely to satisfy coverage.
>
> For this release:
>
>     historical-stratum enrichment is intentionally unsupported
>     until a specific scholarly stratum source is selected and attributed.
>
> This is an OWNER SCOPE DECISION, not an external-source claim.

**What this is not.** It is not `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`. Nobody has established
that no lawful attributed stratum source exists — several do, and each is one scholar's
position. The block is that this release declines to pick one, and declining to pick is a scope
decision the owner owns. Calling it source-unavailable would be the inverse of inferring absence
from not looking: inferring unavailability from not choosing.

**What it forbids concretely.** No stratum nodes. No stratum edges. No `stratum`,
`period`, `chronological_layer` or equivalent property on `:Mantra`, `:Passage`, `:Hymn` or
`:Work`. Veda membership is not a period and must not be presented as a proxy for one. The five
requirements above are conjunctive: a map carrying four of them is still refused.

**Where the axis is currently absent, correctly.** `/api/v1/ask` refuses dating questions
(`ASK_PRODUCT_V1_BENCHMARK_FINAL` Q22), and the capability catalogue publishes no dating card
among its 22. Benchmark V3_3 Q24, Q30 and Q70 are unanswered on this axis by decision, not by
oversight.

`GAP-SEMANTICS-004` closes `CLOSED_SCOPE_DECISION` citing this section. Its own closure test
offers two disjuncts and this is the second: *"the absence is recorded as a deliberate decision
with its reasoning."* The self-citation the R1 pass named as the registry's weakest closure is
gone — the decision is now written outside the audit that closed it.

## 35. OWNER_DECISION_ENTITY_008_DEITY_MEMBERSHIP — two predicates, one product surface

Recorded verbatim, as the owner gave it:

> canonical product Deity membership
> and
> source/addressability-as-deity evidence
>
> are NOT the same semantic predicate.
>
> An entity may be addressed, invoked, personified, or treated ritually in a source without
> automatically belonging to the canonical product Deity class.
>
> Therefore:
>
>     d.is_deity
>
> is the authoritative PRODUCT Deity-membership predicate.
>
> Other source-level predicates remain evidence about source usage.

**Why the old measure was wrong, proven before it was replaced.** `GAP-ENTITY_COVERAGE-008`
carried this closure measure:

```cypher
MATCH (d:Devata)
WHERE (coalesce(d.structure,'UNSPECIFIED') IN ['HUMAN','PATRON_PRAISE','UNSPECIFIED'])
      <> (d.is_deity = false)
RETURN count(d)
```

It returns 29, and it returns 29 *by construction*. Measured 2026-09-18, the 29 decompose
exactly: **28 `ABSTRACT` labels ruled `NOT_DEITY`**, which the structure predicate admits
because `ABSTRACT` is not in its exclusion set, and **1 `UNSPECIFIED` label ruled `DEITY`** —
`VG:DEVATA:SUNAH`, the dog — which the structure predicate excludes. Driving that measure to 0
requires either admitting 28 abstractions each carrying its own recorded refusal reason, or
expelling the dog on the recorded ground that *"excluding this one because its structure is
`UNSPECIFIED` rather than `INDIVIDUAL` would be excluding on a morphological accident."* Both
are overturning recorded curation to satisfy a metric. Refused.

**And the coincidence that hid it.** The entry's own closure *test* reads *"counts over it
exclude the 29 non-deities"* — and that 29 is a **different 29**: 22 `HUMAN` patrons plus 7
`PATRON_PRAISE` gift-praise labels, the figure `deity_eligibility`'s docstring opens with. Two
unrelated quantities that both happen to equal 29, one in the test and one in the measure, is
why a measure comparing the wrong two things read as though it were checking the test. This is
the project's own recorded trap — *a grade can be wrong while every figure is right* — and it
is the reason the measure is replaced rather than merely re-run.

**The replacement measure: product consumer consistency.** Not predicate equality. What must
hold, and what is now pinned by a regression test:

1. every product surface derives Deity membership from the authoritative predicate
   `deity_eligibility.ELIGIBLE_DEITY_PREDICATE` (`d.is_deity = true`);
2. no consumer substitutes a source-level predicate — `structure`, `MENTIONS_DEVATA`,
   addressability — for product membership;
3. the divergence is documented, here and on the entry;
4. a regression test pins the divergence as intentional, so a future pass cannot "fix" it by
   flattening one predicate into the other;
5. no stale consumer still exposes the former 184-node population.

**The 29 stays, and is now a documented invariant rather than a defect.** `structure` remains a
fact about every row and is still asserted to partition, because an unknown structure value must
fail a test rather than quietly shrink the pantheon.

## 36. What round five does not decide

It does not decide the four staged-material gates (A, C, E) — §29 and §33 stand. It does not
authorise any audio verdict: the queue still holds 1,021 `NEEDS_AUDIBLE_REVIEW`, 0 verified, 0
rejected, and §14 stands. It does not grade Ask. And it does not close any entry on unfinished
implementation: an entry with work left in it stays `STILL_IMPLEMENTATION_FIXABLE` and is
counted, which is the guard §29 built.

# Owner round six — Release Blocker Closure R4

One correction, and it is about provenance rather than about content.

## 37. §34 is OWNER-SUPPLIED, and here is the attestation it was missing

The R3 hostile pass upheld a narrow objection to §34 and it was a fair one:

> claim 3 SEMANTICS-004 UPHELD_WITH_QUALIFICATION: the decision and the closure landed in the
> same commit, so the citation is independent at file level and not at change-set level, and
> nothing attests the owner authored it.

That is exactly right, and it is a real limit on what a self-recorded owner decision can prove.
A section an agent writes and then cites in the same change-set is independent of the audit only
in the weakest sense: a reader can find it in a different file, but nothing tells them whose
position it is. Writing the decision down does not establish authorship of it.

**The repository owner has now supplied the decision directly, in the R4 instruction, and it is
reproduced below as given:**

> OWNER_DECISION_SEMANTICS_004_STRATUM_MAP
>
> VedAnvaya will not ingest or publish an unattributed historical/chronological stratum map.
>
> A stratum assignment requires:
>
>     named scholarly source
>     identifiable scholarly work
>     attributable methodology
>     source-local citation
>     provenance to the specific assignment
>
> Named asserter alone is insufficient.
>
> No generic synthesized/model-generated/unattributed stratum map is to be created for this
> release.
>
> Historical-stratum enrichment is intentionally unsupported until such a source is selected
> and attributed.

It agrees with §34 clause for clause: the same five conjunctive requirements, the same rejection
of a named asserter as sufficient, the same refusal of a synthesized map, and the same statement
that the enrichment is intentionally unsupported rather than unavailable. §34's content stands
unchanged.

**What changes is its provenance classification.** §34 is hereby marked **OWNER-SUPPLIED**, not
agent-inferred. The attestation is the R4 instruction itself, which states "Treat this prompt as
owner-supplied instruction" and "The repository owner explicitly confirms the following
decision". The independence is now at instruction level rather than at file level, which is the
strongest attestation available to a repository that has no signing authority for its owner.

**The distinction is worth keeping generally**, because §34 was not the only section at risk of
it. A decision in this file is one of:

| provenance | what attests it | what it can be cited for |
| --- | --- | --- |
| `OWNER-SUPPLIED` | an owner instruction quoting the decision, cited by round | a `CLOSED_SCOPE_DECISION` |
| `AGENT-INFERRED` | an agent's reading of prior decisions | nothing; it must be escalated first |

§34 and §35 are both `OWNER-SUPPLIED`: §35's text is likewise recorded verbatim from an owner
instruction, and §34's attestation is this section. An agent-inferred section has never been
used to close an entry, and must not be.

**`GAP-SEMANTICS-004` is not reopened.** Its status, its basis and its citation are unchanged;
only the provenance line is corrected. R4's instruction is explicit that recording this
correction is the whole of the work: *"Do not reopen SEMANTICS-004 after recording that
provenance correction."*

# Owner round seven — Release Blocker Closure R5

Two decisions the registry had been holding two entries open for. Both were supplied directly
in the R5 instruction, which states they were "explicitly made by the owner after R4" and
"are NOT agent-inferred". Both are therefore `OWNER-SUPPLIED` under the §37 provenance table,
and both may be cited by a closure.

## 38. `OWNER_DECISION_ENTITY_001_EPITHET_SCOPE` — the denominator is the curated inventory

**Decision, as given:**

> For this release, the Epithet completeness denominator is:
>
>     the currently curated, evidence-backed Epithet inventory
>
> not an arbitrary requirement to span "well beyond 4 deities".
>
> The phrase "well beyond 4 deities" has no numerical denominator and no cited source defining
> the target inventory. Therefore it is NOT a valid release gate.
>
> Rules: process every currently curated Epithet; preserve provenance; normalization may
> connect evidence to an existing identity; normalization must never mint a new identity;
> broader epithet discovery is future enrichment, not release completeness.

**Why the clause could not be evaluated.** `GAP-ENTITY_COVERAGE-001`'s second clause asks the
epithet inventory to reach "well beyond 4 deities". R4 recorded that the clause can be neither
passed nor failed: the 13 curated epithets belong to 4 deities, so the occurrence layer can
only ever reach those 4, and no published epithet index exists in this repository against
which 4 could be measured as incomplete. A gate that cannot fail is not a gate — this ledger
has recorded that finding twice (§21, §23) and replaced both offenders.

**Readback, measured 2026-09-18 against the live store, not taken from R4's receipt.** 13
`:Epithet` nodes; 1,035 `MENTIONS_EPITHET` edges between an `:Epithet` and a `:Passage`, up
from 0 edges of any type; 0 epithets reaching no passage; 4 distinct deities, unchanged and
unchangeable without curation. Per-epithet occurrence is carried per node — `occurrence_mantras`,
`occurrence_tokens`, `occurrence_match_tier`, `occurrence_scope` and `occurrence_contract` —
so recall is measured per epithet rather than asserted as one aggregate, which is the third
clause. The inventory is still the curated 13: `fold_alias` was used to compare and never to
create or merge an identity, so the "normalization is a comparison instrument, never identity
evidence" invariant of §2 holds.

**`GAP-ENTITY_COVERAGE-001` closes `CLOSED_DERIVED`** citing this section. The epithet
inventory was not expanded to raise the deity count.

## 39. `OWNER_DECISION_COMMUNITIES_002_PAIR_DECOMPOSITION` — candidates are not evidence

**Decision, as given:**

> Mechanical pair generation is candidate generation, not evidence.
>
> For this release: only pair decompositions supported by canonical identity plus
> source-explicit or deterministic evidence may be asserted.
>
> The remaining mechanical candidates are NON-ASSERTED CANDIDATES, not missing graph data.
>
> Closure denominator: all evidence-eligible pairs processed. NOT: all mechanically generated
> candidates imported.

**Readback, measured 2026-09-18.** Of 214 `:Devata`, 71 carry `structure` PAIR or GROUP — 38
PAIR and 33 GROUP. All 71 carry a typed `decomposition_status` and 0 are null: 16
`DECOMPOSED_FROM_THE_COMPONENT_REGISTRY` (32 `COMPOSED_OF` edges), 4
`NOT_ENUMERABLE_DECLARED_BY_THE_REGISTRY` carrying the registry's own evidence and review
status, and 51 `NOT_ENUMERABLE_FROM_ANYTHING_HELD`. The entry's own closure measure —
PAIR-or-GROUP deities with `component_count` 0 — reads 55, and every one of the 55 is a typed
non-assertion rather than an unprocessed row.

**The evidence-eligible set is exhausted.** `devata_components.yaml` is the only artifact in
this repository that states a composite deity's members. It declares 20 composites; 14 were
already landed; of the remaining 6, four declare an empty member list with an explicit reasoned
refusal and a review status (`REJECTED` for viśvedevāḥ, ādityāḥ and marutaḥ; `NEEDS_REVIEW` for
dyāvāpṛthivyau), and two were landable and landed. So of the 24 pairs a mechanical pass
proposes, 2 are evidence-eligible and 22 are not, and the 22 have no entry in the only artifact
that could make them eligible. Enumerating them means deciding which deities each contains,
which is curation.

**This decision generalises, and it is applied once more in R5.** `GAP-RITUAL-005`'s second
clause has the identical shape: "every modelled rite carries its offerings" is unsatisfiable
from held evidence *because* the same test's third clause forbids presenting co-occurrence as an
asserted offering, and the only rite-to-offering material in the acquired apparatus is 258 rows
staged `PROBABLE`. Under this section's stated principle the 258 are non-asserted candidates,
the closure denominator is the evidence-eligible set, and the honest fix is a typed per-rite
offering status rather than an import. R5 applies it that way and says so, so that a reader can
see the extension and reject it if the owner did not intend it.

**`GAP-COMMUNITIES-002` closes `CLOSED_DERIVED`** citing this section. No unsupported pair was
imported to reach a count.

# Owner round eight — Release prep

Two decisions the registry had been holding its last two entries open for, both against
`OWNER_DECISION_E_AUDIO_GATE`. Both were supplied directly in the release-prep instruction,
which states "These decisions are explicitly supplied by the repository owner" and directs
that they be recorded "as OWNER-SUPPLIED". Both are therefore `OWNER-SUPPLIED` under the §37
provenance table.

`OWNER_DECISION_E_AUDIO_GATE` is not lifted by either. §14 stands unchanged: the 1,021-row
audible queue remains mandatory, no automated check may relabel a row, and the audio domains
stay blocked behind it. What these two decisions establish is the gate's **extent** — what it
was ever about — and what Product V1 requires of the object side of the melodic layer.

## 40. `OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO` — the audible gate covers audio, not notation

**Decision, as given:**

> The audible-review gate applies to AUDIO only.
>
> It does NOT gate textual/musical notation.
>
> Therefore source-explicit Samavedic notation may be released when:
>
>     recension is compatible with the canonical Kauthuma Arcika corpus;
>     canonical coordinate alignment is verified;
>     notation is actually supplied by the source rather than inferred;
>     existing validation gates pass.
>
> No human listening is required for notation.
>
> Uncertain or unaligned notation remains withheld.
>
> Apply this decision to: GAP-SAMAVEDA_MUSIC-002.
>
> Do not pretend notation is audio.

**What this corrects.** `data/staging/integration/wave3_eligibility.json` has the
`samaveda_music` domain `BLOCKED` by `OWNER_DECISION_E_AUDIO_GATE` — the same gate as
`audio_rv`, `audio_av` and `audio_yv`. But 1,136 of that domain's 1,471 rows are
`ARCIKA_NOTATION`: combining Devanagari tone marks printed on verse text. Nothing in them is
a recording, and no amount of listening could verify or refute one. The domain was standing
behind a gate that could never have been the right gate for most of its rows.

**This decision is a permission, not a closure, and the four conditions are measured here
rather than assumed.** Three hold and one does not.

| condition | verdict | measurement |
| --- | --- | --- |
| recension compatible with the canonical Kauthuma arcika | **MET** | `proofs/recension.md`: source page-title prefix `samavedah/kauthumiya/samhita/`; the accented witness's own headers run `purvarcikah/chanda arcikah` through `uttararcikah/navamaprapathakah`, which is the Kauthuma arrangement and not Benfey's six-book Ranayaniya; 1,136 verses byte-identical under the declared normalisation to the text already held at `VG:WORK:SV:KAU`. `recension.no_foreign_recension_inside_kauthuma` evaluated 1,132 records for eight foreign-recension markers, 0 hits. |
| canonical coordinate alignment verified | **MET for 1,136, and only those** | `arcika_notation.text_redderives` 1,136 evaluated / 0 failures, stratified CHANDA 471, ARANYA 31, MAHANAMNYA 3, UTTARA 631; pairing order-consistent under an LCS alignment, not merely set-equal. `identity.uuid_recomputes_from_urn` 1,136/0 and `identity.keys_and_urns_unique` 1,132/0. The other **708** arcika verses are staged `UNRESOLVED` because the accented witness disagrees with our text there; they are what this decision's own "uncertain or unaligned notation remains withheld" clause withholds. |
| notation supplied by the source, not inferred | **MET** | `arcika_notation.tone_mark_present` 1,136/0 — every released row carries a real mark. `arcika_notation.no_pua_no_u0301` 1,136/0 refuses both the private-use-area font hack and the U+0301 acute, the second of which is the fold trap that makes an IAST śa indistinguishable from an udātta. `proofs/notation-codepoint-census.json` counts 108,160 cantillation marks over 1,750,419 characters, 98.09% of them real combining Devanagari Extended U+A8E1–U+A8F1. The notation is recorded as codepoints and never interpreted into pitch: the Kauthuma decipherment authority (van der Hoogt 1929) is not held, and Howard 1988 is Jaiminiya and was deliberately not applied. |
| existing validation gates pass | **NOT MET** | Gate A is `PASS` — the structural validator at full evaluation coverage with `--graph` — and the domain's own QA report is 12 checks, 11,193 records, 0 defects. But `wave3_eligibility.json` records Gate B `UNKNOWN` ("no semantic review recorded") and Gate C `NOT_RUN` ("adversarial test not yet performed"), against a stated eligibility rule of **A and B and C all PASS**. |

**The fourth condition is not a technicality and it is not being read conveniently.** Gate C
is an *independent* falsification attempt, and this campaign's own rule records why that
matters: "Four of four domains adversarially tested so far have failed C, and two of those
four had every aggregate count survive." The adversarial sample inside the artifact — the 40
shortest arcika verses carrying a gana rendering, 0 defects — is the agent's own check on its
own work, which is the thing Gate C exists because it is not. Reading "existing validation
gates" as Gate A alone would clear the board by narrowing a word.

**Consequence.** The notation is **authorised and not yet released**. The audio gate no longer
stands in front of it, so `GAP-SAMAVEDA_MUSIC-002` leaves `BLOCKED_OWNER_DECISION_REQUIRED`;
but nothing was imported, the graph still holds no melodic layer of any kind, and a staged and
unimported domain is not closed — this ledger has recorded that once already, when 944
Atharvavedic translations were described as "closed via the Wayback Machine" against a graph
holding none of them. The entry therefore reads `STILL_IMPLEMENTATION_FIXABLE`, with the
remaining work named exactly: run Gate B and Gate C for `samaveda_music`, then import the
1,136 aligned `ARCIKA_NOTATION` rows and leave the 708 unresolved ones withheld.

**If the owner intended "existing validation gates" to mean the structural validator alone**,
that is a one-line change to the ruling for this entry in
`scripts/wave4_registry_closure_audit.py` and the release-prep report says so plainly rather
than making the choice quietly. It is recorded as unmet because the conservative reading is
the one that cannot manufacture a closure.

> **Answered, and the conservative reading stood — see §42.** The owner ruled 2026-09-18
> that "existing validation gates" means Gate A *and* Gate B *and* Gate C. Nothing above is
> relaxed: the fourth condition was satisfied by building and running the two missing gates,
> Gate C found a real defect in the withheld population's stated reasons, and the notation
> was then imported. `GAP-SAMAVEDA_MUSIC-002` is now `CLOSED_SOURCE_ACQUIRED`; the
> "`STILL_IMPLEMENTATION_FIXABLE`" and "authorised and not yet released" above are this
> section's state as of 2026-09-18 and not the current one.

## 41. `OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1` — no object side, no `MUSICALIZED_AS`

**Decision, as given:**

> For Product V1, MUSICALIZED_AS relationships are NOT required unless the object-side Gana
> identity is independently established and canonical.
>
> Current state:
>
>     no canonical Gana nodes exist;
>     four proposed Gana Works remain PROPOSED_FOR_LEAD_ADJUDICATION.
>
> Do NOT mint Gana nodes or MUSICALIZED_AS edges merely to satisfy a denominator.
>
> The missing object-side Gana model is outside the Product V1 bounded corpus and is future
> enrichment once a Gana corpus/object identity and reliable alignment are established.
>
> This is:
>
>     CLOSED_SCOPE_DECISION
>
> not:
>
>     BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE
>     missing engineering
>     verified zero

**Readback, measured 2026-09-18 against the live store rather than taken from a receipt.**
Every factual premise the decision states is true as given. `MUSICALIZED_AS` carries 0 edges
and the relationship type is absent from `db.relationshipTypes()` entirely. No label matching
`saman|gana|stobha|melod` exists. 0 nodes carry any property whose key contains `gana`. There
are 4 `:Work` nodes and exactly one is Samavedic, `VG:WORK:SV:KAU`; the four gana Works in
`data/staging/samaveda_music/gana_works.jsonl` all read
`identity_status: PROPOSED_FOR_LEAD_ADJUDICATION` and none is in the graph.

**The exclusion is already declared, which is what makes this a scope decision rather than a
convenient one.** `VG:WORK:SV:KAU` carries an `excluded_corpora` list naming
`SAMAVEDA_GRAMAGEYA_GANA`, `SAMAVEDA_ARANYAKAGEYA_GANA`, `SAMAVEDA_UHAGANA` and
`SAMAVEDA_UHYAGANA`, and a `scope` property that states the gana collections "require their
own work_id". `GAP-SAMAVEDA_MUSIC-001` already closed `CLOSED_SCOPE_DECISION` on precisely
that citation. This decision extends the same boundary to the *predicate* that would have
crossed it.

**Applied to `GAP-SAMAVEDA_MUSIC-003` clause 2, which is the whole of what that entry was
blocked on.** Clause 1 closed at R5 and is unmoved: all 1,844 Samavedic mantras carry the
source's own printed running Samhita number, 1,844 distinct values, 0 null. Clause 2 asked
that re-deriving the 495 `MUSICALIZED_AS` edges from the graph alone reproduce all 495; under
this decision those edges are not required for Product V1, the object side they would point at
is outside the bounded corpus, and minting them to reach 495 is the exact act the decision
forbids. **`GAP-SAMAVEDA_MUSIC-003` closes `CLOSED_SCOPE_DECISION`** citing this section. No
gana node was minted and no edge was created.

**The 495 edges are not deleted, denied or forgotten.** They remain staged in
`data/staging/samaveda_music/`, re-verified 495/495 against the graph's own stored arcika
text, and they become importable the moment a gana corpus carries a canonical object identity.
That is future enrichment, which is what the decision says it is.

## 42. `OWNER_DECISION_H_GATES_MEANS_A_AND_B_AND_C` — the fourth condition, answered

**Decision, as given (OWNER-SUPPLIED, 2026-09-18):**

> "existing validation gates" means ALL APPLICABLE validation gates:
>
>     Gate A
>     Gate B
>     Gate C
>
> NOT Gate A alone.
>
> Do NOT weaken the decision to clear the registry.

**What it answers.** §40 released Samavedic notation on four conditions and recorded three
as met and one as not. The unmet one was "existing validation gates pass", and §40 said in
its own last paragraph that if the owner meant the structural validator alone, "that is a
one-line change to the ruling for this entry". The owner has ruled the other way. The
conservative reading stands, so nothing in §40 is relaxed and the remaining work is exactly
what §40 named: run Gate B and Gate C, then import.

**The gates were built and run rather than asserted.** `wave3_eligibility.json` recorded
Gate B `UNKNOWN` ("no semantic review recorded") and Gate C `NOT_RUN` ("adversarial test not
yet performed"), so there was nothing to re-execute — both are new implementations, one file
each, deliberately separate so the same codepath cannot validate itself.

| gate | implementation | population | result |
| --- | --- | --- | --- |
| A | `scripts/validate_staging_artifact.py --graph` | 1,471 rows, 16 checks | **PASS**, every check at full coverage, 0 defects |
| B | `scripts/samaveda_music_gate_b.py` | 1,136 notation rows + the 708 withheld | **PASS**, 12 checks, 12,782 row-evaluations, 0 defects |
| C | `scripts/samaveda_music_gate_c.py` | 1,136 + a declared 40-row adversarial sample | **SURVIVED** — but only after it found a defect and the defect was fixed |

**Gate C landed, which is the point of having it.** Its first run
(`data/staging/samaveda_music_002_final/gate_c_run1.json`) is preserved as a failing run:
39 of the 708 withheld verses stated a reason this repository itself disproves. 5 said "the
accented witness plausibly does not carry this verse at all" and 34 blamed a philological
disagreement, while the verse's exact normalised text is *released, with notation*, on a
coreferent twin elsewhere in the corpus — so the witness demonstrably carries it. The
measured mechanism is line exhaustion, not absence: 153 of the 202 repeated-text groups have
every member released, so the witness does print a repeat twice and the harvest does find
both lines; where only one is released the single order-consistent occurrence went to the
earlier verse. A third reason class,
`WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT`, now carries those 39.

**The fix moved no row and invented no notation.** All 39 remain withheld. Marks belong to
the coordinate the source printed them at, and copying a twin's onto another verse because
the consonants agree would be manufacturing source-explicit data — the one act §40 forbids
outright. Only the stated reason changed, the original is preserved on every corrected row,
and the correction is an overlay
(`data/staging/samaveda_music_002_final/withheld_reason_overlay.json`) rather than an edit:
`data/staging/samaveda_music/` is checksum-sealed, Gate A verifies all twelve digests, and
the generator that produced it is not in this repository, so an in-place edit could not be
re-derived and would have destroyed the witness record it replaced.

**What made Gate C independent, since that was §40's whole objection to the artifact's own
adversarial sample.** It never reads `payload.tone_stripped_text`, the artifact's own QA
report, or the graph's stored SV text. It re-implements the declared normalisation from the
manifest's prose using the Unicode character database in place of the artifact's hard-coded
integer ranges, applies it to the raw witness string, and compares against the canonical
FILE. And it carries a negative control, which is what makes the positive result mean
anything: **1,136 of 1,136 aligned versus 0 of 1,136 shifted by one verse**, same fold, same
rows. Two further independent checks: the witness's own printed numerals, which the
artifact's `mapping_method` states the join did not use, agree with either the dasati-local
verse index or the R5 running Samhita series on **863 of 863** rows that carry one; and the
77 rows pinned by nothing but order — a repeated text with no printed numeral — are **77 of
77** bracketed by two independently pinned anchors. A character census of everything the
strip removes returns **0 undeclared removals**, which is what rules out the match having
been manufactured by over-normalising. The artifact's own 40-row sample is kept and
re-reported, labelled as covering `GANA_RENDERING` and not this population.

**Consequence: released.** 1,136 accented witness TextVersions landed on the
`PARALLEL_WITNESS` surface the product already renders, with the primary text unmoved at the
head of the surface preference. All 1,844 Samavedic verses now carry a typed notation
disposition — 1,136 `SOURCE_EXPLICIT_PRESENT`, 708 `WITHHELD` with the reason class and the
reason prose on the verse itself — because a layer that publishes only its positive rows
lets a reader infer a zero the data never stated. 0 Gana nodes, 0 `MUSICALIZED_AS` edges and
0 melodic labels were created: §41 is untouched. Nothing is interpreted into pitch.

**Coverage is published as four figures and not one**, because a bare 1,136 hides which
arcika a reader can and cannot see: CHANDA 471/585, ARANYA 31/55, MAHANAMNYA 3/10, UTTARA
631/1194.


# Owner round nine — The audio sample, listened to

## 43. `OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE` — sample-level, and it says so

**Decision, as given (OWNER-SUPPLIED, 2026-09-18):**

> The owner manually listened to 20 recordings from the deterministic VedAnvaya owner audio
> sample.
>
> All 20 reviewed recordings matched their expected Vedic passage/audio mapping.
>
> No reviewed recording was rejected and no effective uncertain verdict remains.
>
> The owner accepts this sample as sufficient release-level audible QA of the automated
> audio acquisition and mapping pipeline.
>
> This is SAMPLE-LEVEL validation. It does NOT mean every queued recording was individually
> heard.

**The first audio anyone has heard in this campaign.** §32 recorded 0 of 1,021, three passes
running. 20 rows of the seeded 100-row sample now carry a verdict from a named listener, all
20 `AUDIBLY_VERIFIED`, every one of them with the decoded file's sha256 and byte count on the
row. They fall in one stratum, `AV_COORDINATE_REMAPPED` — 20 of that stratum's 75 sampled
rows — which is worth stating plainly: this is evidence about the Atharvavedic coordinate
remap that GAP-AUDIO-002 measured, and it is *not* evidence about the Rigvedic, Yajurvedic or
Samavedic strata, none of which has been heard.

**One verdict was corrected, and the correction appends.** Row 17 of the decision log
recorded `AUDIBLE_REVIEW_UNCERTAIN` on an accidental keypress; the owner states the recording
was played and matched. The repair is a 21st line with the same row key, not an edit: the log
is the record of what a person typed and when, and a log you may rewrite is not one. Line 17
is byte-identical to what it was, `decisions_by_row` takes the last line per key so the
effective verdict is `AUDIBLY_VERIFIED`, and the summary names the supersession rather than
letting a reader discover it by diffing.

The correction performs no playback and claims none. `new_playback_performed` is `false`, the
superseded row's audio file, sha256 and byte count are carried forward verbatim and flagged
as carried, and `reviewed_at` still reads the original hearing. **20 recordings were heard and
21 lines were written**, and the artifacts state both so the two can never be added up.
Correcting *to* `AUDIBLY_VERIFIED` is refused outright when the superseded row records that
nothing played — a correction may repair an input, never supply a hearing.

**What is accepted, in the two figures that must not be confused:**

| | |
|---|---:|
| `AUDIO_OWNER_SAMPLE` | **ACCEPTED** |
| `SAMPLE_REVIEWED` / `SAMPLE_VERIFIED` | 20 / 20 |
| `SAMPLE_UNCERTAIN` / `SAMPLE_REJECTED` | 0 / 0 |
| queue rows **not individually heard** | **1,001 of 1,021** |
| queue rows promoted by this decision | **0** |

**`OWNER_DECISION_E_AUDIO_GATE` is not lifted.** §14 stands unchanged: the 1,021-row queue
stays mandatory and no automated check may relabel a row. Acceptance of a sample is not a
licence to relabel the population it was drawn from, so `GAP-AUDIO-002`, `-003` and `-004`
stay `NEEDS_AUDIBLE_REVIEW` — their release requirement is the promotion of 954 staged rows
into the product catalogue, which is what §14 gates, and not the acceptance of a sample. What
this decision closes is the owner *execution* task the release-prep receipt was holding open
as `AUDIO_SAMPLE_REVIEW: PENDING_OWNER`.

**Every figure above is recomputed, not typed.**
`data/staging/release_prep/record_audio_sample_acceptance.py` replays the decision log, counts
the live queue, and refuses to write the acceptance record if what it measures disagrees with
what the decision asserts — which was checked by mutation: dropping the correction, promoting
one queue row, and flipping `new_playback_performed` each produce a refusal, and the
unmutated inputs produce none. The record is
`data/manual/audio_review/owner_sample_acceptance.json`; it and the mechanism are held by 15
tests in `tests/unit/test_review_audio_sample.py`, five of which read the live artifacts
rather than a sandbox.

# Owner round ten — Audible review becomes a badge

## 44. `OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION` — visibility and verification are separated

**Decision, as given (OWNER-SUPPLIED, 2026-09-19):**

> I don't care about Q audio. I want the thing to be done.

**Interpreted, and recorded as interpreted** so the reading is auditable rather than
implicit: potentially usable audio must not be kept invisible merely because it lacks
exhaustive individual human audible review. Human audible review becomes an additional QA
badge, not an absolute visibility gate.

**This supersedes `OWNER_DECISION_E_AUDIO_GATE` in one clause only** — the publication
clause of §8 and §14. §8 and §14 are not edited, and stay above as the record of what was
decided on the day it was decided. What §8 was really protecting is untouched and is now
enforced in code rather than by withholding: **automated checking is not listening**.
`PublicationTier.RELEASED_VERIFIED` cannot be constructed without
`audible_review_evidence` citing a decision row, and `SOURCE_MAPPED_UNREVIEWED` cannot
carry one. Both clauses are mutation-tested: disarm either guard and the refusal stops
happening.

The full record, with the five admission conditions and what may never happen, is
`docs/decisions/OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION.md`.

**What was actually admitted.** 954 withheld staged rows were re-evaluated. All 954 had
their media re-fetched from the publisher on 2026-09-19 — a census, not a sample — and all
954 resolved; the 150 Rigvedic rows additionally re-hashed identical to the sha256 recorded
on 2026-09-15. 946 were admitted and **8 refused**, all eight the Yajurvedic residue whose
source text field is dittographic or truncated, so what the recording says is unknown. This
decision widens what may be published *unheard*; it does not widen what may be published
*unmapped*.

| Veda | `RELEASED_VERIFIED` | `SOURCE_MAPPED_UNREVIEWED` | total |
|---|---:|---:|---:|
| AV | 20 | 5,431 | 5,451 |
| RV | 0 | 10,552 | 10,552 |
| SV | 0 | 0 | 0 |
| YV | 0 | 1,777 | 1,777 |

**Only 20 records in the whole catalogue carry a hearing**, and they are the same 20 rows
`OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE` covers — matched individually by canonical key
*and* by the media URL actually played, because a verdict about one recording of a passage
is not a verdict about a different recording of it. **All 16,834 incumbent records were
classified `SOURCE_MAPPED_UNREVIEWED`**: none of their keys appears in the sample decision
log, so there is no evidence for a reviewed tier and none was invented. The 61 published
rows that sit in the review queue (`RV_1_65_TO_1_70_AFFECTED_SPAN`) still read
`NEEDS_AUDIBLE_REVIEW` with a null reviewer and a null verdict; being queued is not being
heard.

**The 1,021-row queue is unchanged.** Nothing in this decision promotes a queue row,
relabels one, or claims a hearing. `data/staging/audio_review_queue.jsonl` still reads
`NEEDS_AUDIBLE_REVIEW` on all 1,021 rows.

**Every figure above is measured.** `docs/reports/audio/staged_addressability_probe.jsonl`
holds one row per request; `docs/reports/audio/admission_report.json` and
`admission_outcomes.jsonl` hold the per-candidate verdict; the catalogue validator now
carries `tiers_partition_the_catalogue` and `reviewed_tier_cites_a_real_hearing` and passes
both against the live graph.
