# Rigveda Semantic Ontology v1

Ontology version: `rigveda-semantic-ontology-v1`
Acceptance policy version: `rigveda-semantic-acceptance-policy-v1`
Source of truth: [`src/vedagraph/semantic/ontology.py`](../../src/vedagraph/semantic/ontology.py)

This document describes the vocabulary a semantic extraction is permitted to use. It is
fixed **before** any model is asked for anything, which is the only ordering under which
"the model may only use the allowed ontology" means something.

---

## Node types

A semantic node is a **reusable knowledge entity**, not a token. Every ordinary noun in
the Rigveda is not a `CONCEPT`. The set is chosen to be usable across the four Vedas,
because a type invented for one text is wrong for the next.

| type | for |
|---|---|
| `CONCEPT` | a reusable idea |
| `PHILOSOPHICAL_CONCEPT` | a subtype of `CONCEPT` for metaphysical and ethical terms |
| `THEME` | what a passage is about, as a reusable label |
| `RITUAL` | a named ritual act |
| `OFFERING` | something offered |
| `SUBSTANCE`, `PLANT`, `ANIMAL`, `OBJECT` | material things |
| `PLACE`, `RIVER`, `REGION` | geography |
| `NATURAL_PHENOMENON` | dawn, thunder, flood, drought |
| `COSMIC_ENTITY` | sun, sky, waters as cosmic bodies |
| `ACTION` | slaying, releasing, pressing, kindling |
| `QUALITY`, `STATE` | attributes and conditions |

### `PHILOSOPHICAL_CONCEPT` is available and empty

The subtype exists so that ṛta, satya, vāc and their kind are not filed next to
"cattle". It is **not seeded**. Nothing in this repository asserts that `RTA` exists
until an extraction proposes it and a reviewer accepts it, and
`data/registry/semantic_entities.yaml` does not exist yet for exactly that reason.

Hard-coding the famous concepts would be writing the answers into the question the pilot
exists to ask, and it would make every later precision figure meaningless: a model that
proposed `RTA` would be scored right because we had already decided it.

---

## Predicates

Fourteen allowed, five refused. There is no sixteenth option: a model's output is
constrained by the JSON Schema to the allowed list, and the validator refuses the
refused list *by name* so a rejection report says which idea was declined rather than
"unknown string".

### Allowed

| predicate | risk | subject → object | auto-acceptable |
|---|---|---|---|
| `PRAISES` | LOW | text → Devatā/Ṛṣi, concept, cosmic entity | `EXPLICIT` |
| `INVOKES` | LOW | text → Devatā/Ṛṣi, cosmic entity | `EXPLICIT` |
| `REQUESTS` | LOW | text → concept, quality, state, object, substance, action, phenomenon | `EXPLICIT` |
| `REFERS_TO_PLACE` | LOW | text → place, river, region | `EXPLICIT` |
| `REFERS_TO_NATURAL_PHENOMENON` | LOW | text → phenomenon, cosmic entity | `EXPLICIT` |
| `INVOLVES_OFFERING` | LOW | text → offering, substance, plant, animal | `EXPLICIT` |
| `INVOLVES_SUBSTANCE` | LOW | text → substance, plant, animal, object, offering | `EXPLICIT` |
| `DESCRIBES` | MEDIUM | text → any | never |
| `DESCRIBES_ACTION` | MEDIUM | text → action | never |
| `INVOLVES_RITUAL` | MEDIUM | text → ritual, action | never |
| `EXPRESSES` | MEDIUM | text → quality, state, concept | never |
| `HAS_THEME` | MEDIUM | text → concept, philosophical concept, theme | never |
| `CONTRASTS_WITH` | MEDIUM | text → any | never |
| `ASSOCIATED_WITH` | MEDIUM | text → any | never |

"Auto-acceptable" is a *ceiling*, not a permission. See the acceptance policy below.

### Refused, with reasons

Named in the enum so that a proposal using one is a recorded policy decision rather than
a parse failure.

| predicate | why not |
|---|---|
| `SYMBOLIZES` | A symbolism claim is a reading of the text, not a report of it, and the Rigveda has several incompatible commentarial traditions of reading it. An edge would silently pick a school. |
| `REPRESENTS` | Same objection, plus ambiguity between "stands for" and "is an instance of". |
| `IS_GOD_OF` | Domain assignment ("Agni is the god of fire") is systematised theology, largely post-Vedic. The Rigveda's own deity scope is already recorded by `HAS_DEVATA` and by what the hymns say. |
| `MEANS` | A meaning claim about Sanskrit made from an English translation is a claim about the translator. Lexical semantics belongs in a lexicon with citations. |
| `CAUSES` | Causal claims inside a mythological narrative are not causal claims about the world, and an edge cannot carry the difference. |

**No `HIGH_INTERPRETATION` predicate is allowed in v1.** A test asserts this, so
promoting one is a deliberate act with a failing build in front of it.

---

## Explicitness

| level | means |
|---|---|
| `EXPLICIT` | stated in the supplied text; a reader can point at the words |
| `STRONG_INFERENCE` | entailed by the supplied text without being stated |
| `INTERPRETIVE` | the model is reading the text |

An `EXPLICIT` claim evidenced only by the Griffith translation is rejected
(`EXPLICITNESS_UNSUPPORTED_BY_EVIDENCE`): "Griffith says so" is explicit about Griffith,
not about the Rigveda.

---

## Acceptance policy

A candidate reaches `AUTO_ACCEPTED` only when **all** of the following hold:

1. it has **no structural fault** — every check in `validate_structure` passes;
2. it does not conflict with the deterministic metadata (that is a review flag);
3. its explicitness is not `INTERPRETIVE`;
4. its predicate is **unlocked**, which happens only when a gold evaluation measured its
   precision at or above **95%**;
5. its explicitness is in that predicate's `auto_acceptable` set;
6. its confidence clears the predicate's floor.

### Confidence is not truth

A model's confidence is produced by the same process that produced the claim, so it
carries no independent information about whether the claim is right. It is a **floor
inside a predicate's own rule** and nothing else. A confidence of 1.0 on a locked
predicate is accepted at exactly the same rate as a confidence of 0.4: not at all.
A test asserts this.

### Nothing is unlocked

`unlocked_predicates` defaults to the empty set, and the gold worksheet is currently
unannotated, so a run today accepts **nothing** automatically and routes every clean
candidate to human review. That is the correct state for an unmeasured pipeline, not a
temporary inconvenience: acceptance is earned by measurement, and no measurement has
been made.

---

## Deterministic context conflict

A `PRAISES` or `INVOKES` claim naming a Devatā the Anukramaṇī did not assign to that
mantra raises `DETERMINISTIC_CONTEXT_CONFLICT` and goes to review. It is **not**
rejected. Traditional assignment and textual content diverge constantly — 3,992 mantras
in the pinned build carry no lexical mention of any deity at all, assigned or otherwise
— and a pipeline that rejected the divergence would be enforcing the Anukramaṇī onto the
text, which is the exact conflation `ADR-013` exists to prevent.
