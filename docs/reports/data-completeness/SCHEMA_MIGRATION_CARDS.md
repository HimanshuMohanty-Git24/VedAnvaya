# Schema migration cards

Owner decision 3 approves the four additive extensions in principle, subject to each card
demonstrating all five flags. A card with `OLD_PREDICATE_MEANING_CHANGED = true` is not
pre-approved and returns to the owner.

**None of these is applied.** Wave 3 is not authorized and the dry-run has not been
reviewed.

| Card | Domain blocked | Approved by flags? |
|---|---|---|
| M1 `:RoleFiller` | semantic_roles | yes |
| M2 Samavedic running number | samaveda_music | yes |
| M3 four gāna `Work` identities | samaveda_music | yes |
| M4 `MUSICALIZED_AS` range widening | samaveda_music | yes |
| M5 `SPECIALIZED_FORM_OF` | communities / ontology | yes |
| M6 `scope_type` namespacing | attribution + audio | **SUPERSEDED** — see M6′ below |

M5 and M6 were not in the original four. M5 implements owner decision 1. M6 was the
collision the audit found and the one card that failed the flags; the owner's second round
replaced the question it asked, and M6′ below passes all five.

---

## M1 — `:RoleFiller`, `ASSERTION_ROLE`, `ROLE_FILLER_ENTITY`

**Domain blocked.** `semantic_roles`. Without it the role layer cannot be expressed.

**Why the existing schema is insufficient, measured.** `ASSERTION_AGENT` and
`ASSERTION_TARGET` point only at `:Devata` — verified live, 2,502 and 799 edges, all to
`:Devata`. Of the restaged 2,052 asserted fillers only 142 are deities, so **93.1% are
unrepresentable**. The graph already pays this cost silently: 1,364 patients, 366
instruments, 356 beneficiaries and 225 locations sit on `:SemanticAssertion` as opaque
strings with no edges at all. The sharpest case is a filler that is the first-person
worshipper — "grant to us" has a recipient and it is not a god.

**New elements.**
```
(:RoleFiller {role, surface, referent_confidence, source_method, role_derivation})
(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller)
(:RoleFiller)-[:REFERS_TO]->(:Devata|:Object|:Substance|:Plant|:Place|:Concept|:DomainEntity)
```
A `:RoleFiller` is a **role occurrence in an assertion**, not a copy of a canonical entity.
Where it corresponds to a known canonical thing it is connected, never duplicated. It
exists because the occurrence and the thing referred to are different graph objects — the
same deity fills different roles in different assertions.

**Identity rule.** Deterministic URN and UUIDv5 from namespace
`7c8cde94-2bc0-50e2-8819-568ae65a3ec4` via `src/vedagraph/identity.py`, over
`(assertion_id, role, surface_offset)`. No random ids.

**Example staged rows.** `data/staging/semantic_roles/role_fillers.jsonl`, 2,052 rows, all
`TREEBANK_DEPREL`, all `importable: true`. Plus `role_candidates.jsonl`, 15,704 rows, all
`importable: false` — the verification queue, not a weaker grade of fact.

**Backward compatibility.** `ASSERTION_AGENT` and `ASSERTION_TARGET` keep their name,
direction, range and every existing edge. Nothing currently reading them changes behaviour.
The opaque string properties stay in place until a separate decision retires them, so no
reader loses data.

**API consequence.** A new typed role block on the assertion surface. Existing assertion
responses unchanged.

**Frontend consequence.** None required. The role layer is additive and no surface reads it
yet.

**Rollback.** Delete `:RoleFiller` nodes and their two edge types. No pre-existing node or
edge is touched, so rollback is a deletion rather than a restore.

**Migration test.** Every `:RoleFiller` resolves to exactly one `:SemanticAssertion`; every
`REFERS_TO` target exists; the 2,052 count is read back out of the database; and
`ASSERTION_AGENT`/`ASSERTION_TARGET` edge counts are unchanged at 2,502 and 799.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

---

## M2 — a home for the Samavedic running Saṃhitā number

**Domain blocked.** `samaveda_music`. It is the only key joining an Ārcika verse to a gāna
rendering, and it exists nowhere in the graph — so the 495 `MUSICALIZED_AS` edges could not
be re-derived or audited after import.

**Why insufficient.** The Ārcika ingest kept structural coordinates and discarded the
edition's own running number, which was not needed until a second work had to be joined.

**New element.** An additive property `running_samhita_number` on Samavedic `:Mantra`
nodes, 1,844 values, already captured in the agent's `citations.jsonl`.

**Identity rule.** Not an identity element. It is a source-stated locator, and canonical
keys do not change.

**Backward compatibility.** A new property on existing nodes. No predicate, label or key
changes.

**Rollback.** Remove the property.

**Migration test.** All 1,844 Samavedic mantras carry it; re-deriving `MUSICALIZED_AS` from
the graph alone reproduces all 495 edges.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

---

## M3 — four gāna `Work` identities

**Domain blocked.** `samaveda_music`.

**Why insufficient.** Grāmageyagāna, Āraṇyageyagāna, Ūhagāna and Ūhyagāna are four distinct
works. The campaign forbids collapsing Ārcika text, gāna text, notation and performance
into one object, and `VG:WORK:SV:KAU` itself records that the gāna corpus "requires its own
work_id".

**New elements.** Four `:Work` nodes with deterministic URNs and UUIDv5 from the project
namespace, staged `PROPOSED_FOR_LEAD_ADJUDICATION`.

**Rahasyagāna is deliberately not modelled.** Folding it into Ūhyagāna and minting a fifth
Work each assert something unsettled.

**Backward compatibility.** The four core Saṃhitā works are untouched, and core counts must
not move — that is the campaign's hardest boundary.

**Rollback.** Delete the four works and their edges.

**Migration test.** Core corpus counts unchanged at RV 10,552 / SV 1,844 / YV 1,975 /
AV 5,839; the four new works carry no `:Mantra` of the core recensions.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

---

## M4 — widen `MUSICALIZED_AS`

**Domain blocked.** `samaveda_music`.

**Why insufficient.** The ontology reference glosses it RV→SV. It must carry SV→gāna.

**This is the one existing predicate any card touches**, so it needs care. The change is to
the **documented range**, not to the relation's meaning: "X is musicalized as Y" already
means what it needs to mean, and the gloss simply never anticipated a gāna target. No
existing edge changes direction, type or endpoints.

**Backward compatibility.** Existing edges unchanged. A reader filtering on RV→SV still
gets exactly what it got.

**Rollback.** Revert the gloss and delete the SV→gāna edges.

**Migration test.** Pre-existing `MUSICALIZED_AS` edge count unchanged; new edges all have
a gāna `Work` target.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

Recorded reasoning for the last flag: widening a documented range is not changing a
meaning. If review disagrees, this card returns to the owner.

---

## M5 — `SPECIALIZED_FORM_OF`

**Implements owner decision 1.**

**Why insufficient.** `EPITHET_VARIANT_OF` asserts that Soma Pavamāna *is* Soma, while
`DEVATA_TAXONOMY_V1` holds them apart on separate axes. Both are curated and deliberate.
Neither merging the nodes nor weakening the relation generally is acceptable.

**New element.** `(:Devata)-[:SPECIALIZED_FORM_OF]->(:Devata)` — A is a contextually
specialized manifestation of B and remains separately addressable. It must not be read as
an orthographic alias, an epithet spelling, a licence to collapse, or interchangeability in
every query.

**Scope.** One edge: Soma Pavamāna → Soma. The other 10 `EPITHET_VARIANT_OF` pairs were
sampled and are epithets proper.

**Provenance.** The former edge is recorded with old relation, new relation, reason and
migration commit.

**Backward compatibility.** `EPITHET_VARIANT_OF` keeps its meaning and its other 10 edges.
One edge moves; that is a data migration with a recorded reason, not a semantic change to
the predicate.

**Rollback.** Restore the `EPITHET_VARIANT_OF` edge and delete the new one.

**Migration test.** Re-run deity identity invariants, community input population, deity
profile queries, Ask identity and disambiguation tests, and Knowledge World projection
tests. `EPITHET_VARIANT_OF` count goes 11 → 10 and `SPECIALIZED_FORM_OF` is 1.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

---

## M6 — `scope_type` namespacing — **SUPERSEDED, kept as the record**

**The collision.** `attribution` writes `scope_type = SINGLE_MANTRA` meaning the scope of an
attribution assertion. The audio domains write `scope_type = MANTRA` meaning the scope of an
audio record. 18 canonical keys carry both.

**Why this card failed the flags, as recorded at the time.** Any fix changes what an existing
property name means for at least one existing reader:

- Namespace both to `attribution_scope_type` and `audio_scope_type`: existing readers of
  `scope_type` break.
- Namespace only the newcomer: the property keeps two meanings, which is the defect.
- Resolve by precedence: **loses one concept silently.** The collision audit's own second
  pass proposed exactly this, and it was wrong in the direction that destroys data.

```
ADDITIVE = false · BACKWARD_COMPATIBLE = false
OLD_PREDICATE_MEANING_CHANGED = true   ← not pre-approved
```

**The owner asked a different question back.** Not *which readers may break*, but *what is
the truthful scope of each population*. See M6′.

---

## M6′ — `scope_type` derived from the evidence grain, split by population

**Implements owner decision 12.** Replaces M6.

**Two measurements dissolved the original framing.**

`scope_type` is on **0 nodes and 0 relationships** of the live graph. The collision the audit
found is between two *staging* artifacts, so there is no reader in the database whose meaning
could change, and M6's `ADDITIVE = false` / `BACKWARD_COMPATIBLE = false` were recorded
against a population that does not exist.

And the schema already held both vocabularies, already separate:
`product.audio.models.AudioScope` is the tradition's span vocabulary for a recording, with
`SCOPE_TO_ENTITY_TYPES` as its grain contract, and `models.enums.ScopeType` is the scope of a
metadata assertion. Two axes, two closed enums, two Pydantic models — and one property name,
which was the whole defect. So the repair writes each axis under its own name; no vocabulary
had to be invented and no winner had to be picked.

**Three homogeneous populations.** A total partition of the 1,423 scope-bearing rows.

| Population | Property | `scope_type` | Enum | Rows | Grain asserted against the live graph |
|---|---|---|---|--:|---|
| `AUDIO_RECORD_AT_MANTRA_SCOPE` | `audio_scope_type` | `MANTRA` | `AudioScope` | 954 | every subject is `entity_type=MANTRA`, the only type `AudioScope.MANTRA` admits |
| `GANA_PERFORMANCE_AT_COLLECTION_SCOPE` | `audio_scope_type` | `COLLECTION` | `AudioScope` | 3 | every subject is `entity_type=STRUCTURAL_CONTAINER` |
| `ATTRIBUTION_ASSERTION_AT_SINGLE_MANTRA_SCOPE` | `assertion_scope_type` | `SINGLE_MANTRA` | `ScopeType` | 466 | every subject is `entity_type=MANTRA`, and all 466 independently carry `asserted_granularity=VERSE` |

**Why the gāna rows are a population apart** rather than folded into the audio one, though
both are audio: the grain genuinely differs. They are gāna performances of 82s, 223s and 399s
over containers holding many verses, with no source stating a boundary inside any of them.
Labelling them `MANTRA` so one importer could take a single population is what the owner
barred.

**Defect found and fixed.** Those three rows were staged `STRUCTURAL_CONTAINER` — a graph
`entity_type`, and **not a member of `AudioScope` at all**. One axis's value cast into the
other's enum, which is the same shape of error as the name collision it sits inside.
`AudioScope.COLLECTION` is the enum's own value for a named Samavedic collection — "ARANYA,
CHANDA, MAHANAMNYA, UTTARA" — and all three keys are CHANDA or UTTARA containers. The truthful
closed-enum value was already in the schema.

**No population is `UNKNOWN`.** Every source grain here is known, and the owner bars
`UNKNOWN` where it is.

**Identity rule.** Not an identity element. Both are properties on existing nodes; canonical
keys do not change.

**Backward compatibility.** Nothing writes a property called `scope_type`, and none exists in
the graph. Two new property names appear. No predicate, label or key changes.

**Rollback.** Remove `audio_scope_type` and `assertion_scope_type`.

**Migration test.** `scripts/wave3_scope_grain_repair.py` asserts, per population, that the
staged value is a member of its declared enum, that the population is homogeneous, and that
every subject resolves at the grain the enum's own contract requires. It also asserts the
partition is total, so a scope-bearing domain claimed by no population — or by two — is a
failure rather than a silence. Verdict: `HOMOGENEOUS_AND_ON_GRAIN`.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```

**Pre-approved under owner decision 3**, because the flag that sent M6 back is now false and
measured rather than argued.

## M7 — `:RitualStep` product identity

**Owner decision 2.** `HAS_RITUAL_STEP` may not become traversable until the step nodes carry
a product identity that is deterministic, additive, and independent of display text and of
`step_position`.

**What this writes.** One property: `display_type = "RITUAL_STEP"` on 3,121 nodes. That is
all. No node, relationship, label or key is created, moved or removed.

**Why that is the whole migration.** The identity the owner asked for already exists. Wave 3
staged every step with a `step_key`, a `canonical_urn` and a `uuid5` `entity_id`, and the
graph holds all three on all 3,121 nodes. What it does not hold is `display_type`, which
`PRODUCT_TYPE_BY_DISPLAY_TYPE` is keyed on and which every non-internal node in this graph is
contracted to carry. That absence, not the identity, was the reason for the refusal.

**Grain, measured rather than chosen.** `scripts/ritual_step_identity_probe.py` tested three
candidate grains over the 3,123 importable rows:

| grain | distinct values | values covering rows that **disagree** |
|---|---:|---:|
| `SOURCE_OCCURRENCE` (work + coordinate) | 2,767 | 308 |
| `RITE_SPECIFIC_OCCURRENCE` (rite + work + coordinate) | 3,122 | 1 |
| `POSITION_BASED` (rite + `step_position`) | 1,137 | 680 |

A source-occurrence key would merge 308 identities standing for different claims, because one
sutra is cited for several rites. A position-based key fails outright: `step_position`
restarts at 1 inside every work, which is the same measurement that produced 2,666 (rite,
position) collisions and forced the API to group procedure by source work. **The grain is
`RITE_SPECIFIC_OCCURRENCE`**, and the staged `step_key` is already exactly that.

**Identity rule.** Unchanged, and reproduced rather than redefined:

```
key   VG:RITESTEP:<rite>:<work>:<source coordinate>
urn   urn:vedagraph:ritual-step:<rite>:<work>:<source coordinate>
uuid  uuid5(7c8cde94-2bc0-50e2-8819-568ae65a3ec4, canonical_urn)
```

Verified over all 3,123 importable rows: `entity_id` equals `uuid5(namespace, canonical_urn)`
for every one, so the same input reproduces the same identity byte for byte. No component is
display text, normalizer output, or `step_position`, so the identity survives a relabelling, a
transliteration change, a UI change and a reordering of artifact rows.

**The one collision, and why it is not fixed here.** `VG:RITESTEP:VISVAJIT:SankhSS:16:15:13`
covers two printed sutras — ordinals 4535 and 4536 — that the edition the staging read prints
under a single citation. The locator cannot separate them. The pair is withheld from the
graph and stays withheld; the graph holds 0 key, URN and UUID collisions. The only available
discriminator is `printed_ordinal_in_work`, and putting it in the key would change all 3,121
existing identities to accommodate one row. Recorded as a gap against the artifact's locator
extraction instead.

**Backward compatibility.** `HAS_STEP` is untouched and still means what it meant: 3 edges,
the Samhita's own numbering. The two step layers stay distinct in the graph and in the API.
No existing property is overwritten — the migration writes only where `display_type` is null
and refuses to run if any node carries a different one.

**Rollback.** `MATCH (s:RitualStep) REMOVE s.display_type, s.m7_applied`. Nothing else to
undo, and the verified dump covers it regardless.

**Migration test.** `scripts/m7_ritual_step_product_identity.py` asserts, before writing, that
every node carries all three identity components, that key, URN and UUID collisions are each
0, that no node lacks a source locator, and that no node already carries a foreign
`display_type`; and after writing, that the node and relationship deltas are both 0 and the
four corpus totals have not moved. `tests/api/test_graph.py` asserts the traversal returns a
stable product id.

```
ADDITIVE = true · DETERMINISTIC_IDENTITY = true · BACKWARD_COMPATIBLE = true
ROLLBACK_DEFINED = true · OLD_PREDICATE_MEANING_CHANGED = false
```
