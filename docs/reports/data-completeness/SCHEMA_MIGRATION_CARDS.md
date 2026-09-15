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
| M6 `scope_type` namespacing | attribution + audio | **returns to owner** |

M5 and M6 were not in the original four. M5 implements owner decision 1. M6 is the
collision the audit found, and it is the one card that fails the flags.

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

## M6 — `scope_type` namespacing — **RETURNS TO OWNER**

**The collision.** `attribution` writes `scope_type = SINGLE_MANTRA` meaning the scope of an
attribution assertion. The audio domains write `scope_type = MANTRA` meaning the scope of an
audio record. 18 canonical keys carry both.

**Why this card fails the flags.** Any fix changes what an existing property name means for
at least one existing reader:

- Namespace both to `attribution_scope_type` and `audio_scope_type`: existing readers of
  `scope_type` break.
- Namespace only the newcomer: the property keeps two meanings, which is the defect.
- Resolve by precedence: **loses one concept silently.** The collision audit's own second
  pass proposed exactly this, and it was wrong in the direction that destroys data.

```
ADDITIVE = false · BACKWARD_COMPATIBLE = false
OLD_PREDICATE_MEANING_CHANGED = true   ← not pre-approved
```

**The owner's choice.** Which readers may break, and when. The lead's recommendation is to
namespace both and update every reader in the same commit, because a property carrying two
meanings will be read wrongly eventually and the 18 overlapping keys are only the ones we
can currently see.
