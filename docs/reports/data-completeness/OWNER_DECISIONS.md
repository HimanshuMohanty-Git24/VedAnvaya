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
