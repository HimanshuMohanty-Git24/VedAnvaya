---
prompt_version: rigveda-semantic-extraction-v3.2
supersedes_prompt_version: rigveda-semantic-extraction-v3
payload_schema_version: rigveda-semantic-extraction-v3
ontology_version: rigveda-semantic-ontology-v1
semantic_object_schema_version: rigveda-semantic-object-v1
explicitness_policy_version: rigveda-semantic-explicitness-v2
packet_version: rigveda-semantic-evidence-packet-v1
execution_scope: BOUNDED_60_STABILITY_ONLY
execution_status: NOT_APPROVED_FOR_508_OR_FULL_CORPUS
---

# Rigveda semantic extraction — typed objects v3.2

Return only the object required by `semantic_extraction_v3.schema.json`. Every assertion
and object is an occurrence-level candidate for review, never an accepted graph edge or
a global canonical concept. Use only the supplied EvidencePacket. Do not use remembered
Vedic knowledge.

This version changes emission policy only. The payload schema, the fourteen allowed
predicates, the typed-object schema, the EvidencePacket, the CODEX_DIRECT task, receipt and
binding contract, and the explicitness policy are the ones the previous version used,
unchanged — only the policy version each object records is new. It exists because
the previous wording admitted more than one internally coherent reading of *when* a
directly evidenced relation has to be emitted, and two runs over identical packets
occupied different emission regimes as a result. The rules below settle that boundary.
They do not widen what may be claimed.

## Version fields

`prompt_version` inside the returned payload is a field of the payload schema and keeps
its schema value `rigveda-semantic-extraction-v3`. The `prompt_version` on every typed
object records the policy that authored it and must be `rigveda-semantic-extraction-v3.2`.
`object_schema_version` remains `rigveda-semantic-object-v1`.

## Required predicate-family inspection

Inspect all fourteen allowed families independently, in this order, before finalizing any
result — including a result that emits assertions:

1. `INVOKES`
2. `PRAISES`
3. `REQUESTS`
4. `DESCRIBES`
5. `DESCRIBES_ACTION`
6. `INVOLVES_RITUAL`
7. `INVOLVES_OFFERING`
8. `INVOLVES_SUBSTANCE`
9. `REFERS_TO_NATURAL_PHENOMENON`
10. `REFERS_TO_PLACE`
11. `EXPRESSES`
12. `HAS_THEME`
13. `ASSOCIATED_WITH`
14. `CONTRASTS_WITH`

For each family, apply that family's evidence policy from **Object selection** below and
ask one question: does the packet directly support both this relation force and a
bindable target or object? Answer every family before writing output. This is a
checklist, not a quota — a family that fails the test contributes nothing, and no family
is owed an assertion.

The predicate vocabulary is unchanged. Never emit `IS_GOD_OF`, `SYMBOLIZES`,
`REPRESENTS`, `MEANS`, or `CAUSES`, including by hiding one inside `ASSOCIATED_WITH`.

## Emission policy

### Rule 1 — Emit-vs-omit floor

After the fourteen-family inspection, emit every relation for which both hold:

- the relation force is directly supported by the EvidencePacket, and
- the target or object is directly supported and bindable.

Do not omit an independently supported relation merely because another relation has
already been emitted from the same passage. "Optional" describes evidence that leaves a
policy boundary genuinely unresolved; it never licenses skipping a directly evidenced
relation. Remain conservative in the other direction too: do not infer unsupported
semantics to raise assertion density. This rule governs the consistency of supported
emission, not the size of the output.

### Rule 2 — REQUESTS force

Treat as request force any construction in which the speaker seeks an outcome from an
addressee, including:

- an imperative,
- an optative,
- a prohibitive wish,
- an explicit construction of granting, giving, bringing, sending, or bestowing,
- an expressed desired result of the form *may X occur*, *may we receive*, or *may you
  cause*, and directly expressed equivalents.

The requested outcome is the desired resulting state or action. Do not automatically take
the grammatical object of the request verb as the semantic outcome. Do not invent an
addressee or a beneficiary that the evidence does not ground.

### Rule 3 — REQUESTS outcome splitting

Emit one `REQUESTS` assertion per independently coordinated desired outcome. Split only
where each conjunct can stand on its own as a separately desired result. A modifier or a
beneficiary that merely qualifies one result stays inside that one outcome. An unresolved
relative phrase does not become an additional outcome unless its referent or resulting
state is independently anchored in the packet. Avoid both failure directions: collapsing
genuinely independent requests into one, and splitting one complex request phrase into
several.

### Rule 4 — DESCRIBES precedence

Use `DESCRIBES` for an entity-level state, quality, property, role, or depiction directly
attributed to an entity. Where the only semantic content of a clause is an action
performed by or involving the entity, emit `DESCRIBES_ACTION` and do not add a redundant
`DESCRIBES`. Where the passage independently states both an entity-level quality or state
*and* an action, both may be emitted, each with its own valid evidence and binding
anchors. Never duplicate one action into both predicates because it concerns an entity.

### Rule 5 — DESCRIBES_ACTION scope

Use `DESCRIBES_ACTION` only for an action asserted or narrated as occurring. An action
that is commanded or wished for is a desired future action and belongs to `REQUESTS`. An
imperative directed at an addressee is therefore not by itself a narrated action, whatever
verb it uses. If the passage separately states that the action does occur, then
`DESCRIBES_ACTION` may also be supported. Keep relation force distinct from grammatical
surface form.

### Rule 6 — Material and ritual co-emission

A material, substance, offering, or ritual relation may coexist with `REQUESTS`,
`DESCRIBES`, `DESCRIBES_ACTION`, `INVOKES`, `PRAISES`, or another allowed family only when
each relation independently carries direct local evidence. Repeated mentions of the same
passage-level predicate and object do not create duplicate assertions merely because the
word occurs more than once. Separate assertions are appropriate only when distinct typed
roles are expressed, or when materially different qualifiers or relations are
independently supported.

### Rule 7 — No-claim criterion

`no_claim` is permitted only after all fourteen families have been inspected and none
passes the direct test of relation force plus a supported target or object. Do not return
no claim because a passage is difficult, or out of caution, when a supported relation is
available. When no claim is returned, the reason should identify the family or boundary
that failed where that is useful, and must invent no semantics. A no-claim reason is
model-authored diagnostic metadata; it is not canonical knowledge. No-claim may coexist
with ontology-gap records but never with assertions.

## Object selection

- `INVOKES` and `PRAISES`: use `CANONICAL_ENTITY_REF` whenever a supplied deterministic
  entity key resolves the referent. Never create a second candidate for an entity a
  supplied key already names. Use an opaque or ontology-gap object when no supplied key
  resolves the evidenced referent.
- `DESCRIBES`: target the canonical or specific semantic entity being described. Put an
  action in a separate `DESCRIBES_ACTION` assertion under Rule 4; do not fold an action
  into an identity label.
- `REQUESTS`: emit one `REQUESTED_OUTCOME` per outcome admitted by Rule 3. Use a concise
  head; keep explicit qualifiers, beneficiary, and target entity in their own fields. Do
  not copy the translated request sentence into the head.
- `DESCRIBES_ACTION`: use `EVENT` with a concise `action_head`. Supply actor, patient, or
  other participants only when the packet directly supports them. Missing roles stay
  absent. Do not invent a canonical action ontology ID.
- `INVOLVES_RITUAL`: use `RITUAL_EVENT` for an evidenced ritual or event type. These
  remain candidates until reviewed.
- `INVOLVES_OFFERING`: use `OFFERING_REF` for a thing in its offered role. Do not use the
  ritual act, and do not infer that every named substance is offered.
- `INVOLVES_SUBSTANCE`: use `SUBSTANCE_REF` for physical material. Reuse supplied
  deterministic lexical or canonical identity where the schema permits, and preserve a
  distinction the evidence itself draws between a substance and a qualified form of it.
- `REFERS_TO_NATURAL_PHENOMENON`: use `NATURAL_PHENOMENON_REF` for the phenomenon itself.
  A traditional Devatā assignment does not establish this assertion, and a Devatā key is
  not interchangeable with the phenomenon.
- `REFERS_TO_PLACE`: use `PLACE_REF` only for an explicit place or spatial referent. Use
  `OPAQUE_SPATIAL_REFERENT` or review for seat, dwelling, station, world, or mansion when
  geographic or place status is unclear.
- `EXPRESSES`: use `STATE_REF`, `QUALITY_REF`, or `CONCEPT_REF` with a concise evidenced
  head. Do not copy a sentence fragment as identity.
- `HAS_THEME`, `ASSOCIATED_WITH`, and `CONTRASTS_WITH` remain review-sensitive. Emit only
  when the relation is directly supportable and no more specific predicate fits.

For an evidenced human, patron, ancestor, or kinship referent the ontology cannot encode,
use `ONTOLOGY_GAP_REF` with the appropriate `PERSON_LIKE_REFERENT_UNMODELED`,
`PATRON_ROLE_UNMODELED`, `ANCESTOR_ROLE_UNMODELED`, or
`KINSHIP_ROLE_UNMODELED` code. Never force it into `COSMIC_ENTITY`.

## Evidence and identity

Every non-canonical object and every assertion must cite the source passage and at least
one supplied deterministic evidence ID: translation record (plus exact character offsets
when available), Sanskrit token IDs, passage IDs, or another supplied evidence record.
Never invent an ID or use generated reasoning as evidence.

Every assertion also carries its own binding anchors: a `RELATION` anchor on the wording
that carries the relation, a `TARGET` anchor on the wording that identifies a canonical
target, and an `OUTCOME` anchor on the requested outcome itself. An anchor spanning the
whole verse is not assertion-specific evidence. Rules 1 through 6 change how many
relations may have to be emitted; they do not lower this bar for any one of them.

`display_label` is a concise human-readable annotation. It is not identity.
`normalized_head` is a comparison field inside a typed object, not a global concept ID.
Never decide that two objects are equivalent because their labels are equal or similar.

Candidate IDs are assigned deterministically from run ID, mantra ID, predicate, evidence,
and ordinal. They identify occurrences only. Do not mint canonical semantic concept IDs.

## Explicitness

Use `EXPLICIT` when both the relation and target are directly supportable from supplied
Sanskrit or supplied translation evidence. Reliance on the supplied translation does not
by itself make a relation inferential.

Use `STRONG_INFERENCE` only when exactly one limited inferential step is necessary and
name that step in the rationale. If the claim requires broad narrative, symbolic,
theological, thematic, or culturally remembered interpretation, do not emit it.
`INTERPRETIVE` is prohibited. This policy is unchanged by v3.2: the emission floor in
Rule 1 applies only to relations that already meet it, and never relaxes it.

## Status

Output is `CANDIDATE / NEEDS_REVIEW`. No output can unlock a predicate;
`unlocked_predicates` remains empty. Nothing here promotes a candidate to canonical
knowledge, and no human gold set exists against which any of it has been scored.
