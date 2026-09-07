---
prompt_version: rigveda-semantic-extraction-v3
ontology_version: rigveda-semantic-ontology-v1
semantic_object_schema_version: rigveda-semantic-object-v1
explicitness_policy_version: rigveda-semantic-explicitness-v2
packet_version: rigveda-semantic-evidence-packet-v1
execution_status: EXECUTION_APPROVED_V3_PILOT
---

# Rigveda semantic extraction — typed objects v3

Return only the object required by `semantic_extraction_v3.schema.json`. Every assertion
and object is an occurrence-level candidate for review, never an accepted graph edge or
a global canonical concept. Use only the supplied EvidencePacket. Do not use remembered
Vedic knowledge.

## Required predicate-family pass

Before returning no claim, inspect all fourteen allowed families independently:
`INVOKES`, `PRAISES`, `REQUESTS`, `DESCRIBES`, `DESCRIBES_ACTION`,
`INVOLVES_RITUAL`, `INVOLVES_OFFERING`, `INVOLVES_SUBSTANCE`,
`REFERS_TO_NATURAL_PHENOMENON`, `REFERS_TO_PLACE`, `EXPRESSES`, `HAS_THEME`,
`ASSOCIATED_WITH`, and `CONTRASTS_WITH`. Emit multiple assertions when several are
independently supported. An uncertain family produces no assertion or an ontology-gap
record, not a guessed nearest predicate.

The predicate vocabulary is unchanged. Never emit `IS_GOD_OF`, `SYMBOLIZES`,
`REPRESENTS`, `MEANS`, or `CAUSES`, including by hiding one inside `ASSOCIATED_WITH`.

## Object selection

- `INVOKES` and `PRAISES`: use `CANONICAL_ENTITY_REF` whenever a supplied deterministic
  entity key resolves the referent. Never create a second “Agni” candidate. Use an opaque
  or ontology-gap object when no supplied key resolves the evidenced referent.
- `DESCRIBES`: target the canonical or specific semantic entity being described. Put an
  action in a separate `DESCRIBES_ACTION` assertion; do not produce an identity label such
  as “Agni shining brightly”.
- `REQUESTS`: emit one `REQUESTED_OUTCOME` per independently requested outcome. Use a
  concise head such as `protection`, `wealth`, `long life`, or `victory`; keep explicit
  qualifiers, beneficiary, and target entity in their fields. Do not copy the translated
  request sentence into the head.
- `DESCRIBES_ACTION`: use `EVENT` with a concise `action_head`. Supply actor, patient, or
  other participants only when the packet directly supports them. Missing roles stay
  absent. Do not invent a canonical action ontology ID.
- `INVOLVES_RITUAL`: use `RITUAL_EVENT` for an evidenced ritual/event type such as
  sacrifice, Soma pressing, libation, or purification. These remain candidates until
  reviewed.
- `INVOLVES_OFFERING`: use `OFFERING_REF` for a thing in its offered role. Do not use the
  ritual act or infer that every named substance is offered.
- `INVOLVES_SUBSTANCE`: use `SUBSTANCE_REF` for physical material. Reuse supplied
  deterministic lexical/canonical identity where the schema permits; preserve `SOMA`
  versus `PAVAMANA SOMA` when the evidence distinguishes them.
- `REFERS_TO_NATURAL_PHENOMENON`: use `NATURAL_PHENOMENON_REF` for the phenomenon itself.
  A traditional Devatā assignment does not establish this assertion and a Devatā key is
  not interchangeable with the phenomenon.
- `REFERS_TO_PLACE`: use `PLACE_REF` only for an explicit place/spatial referent. Use
  `OPAQUE_SPATIAL_REFERENT` or review for seat, dwelling, station, world, or mansion when
  geographic/place status is unclear.
- `EXPRESSES`: use `STATE_REF`, `QUALITY_REF`, or `CONCEPT_REF` with a concise evidenced
  head such as fear, desire, or yearning. Do not copy a sentence fragment as identity.
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

The expected future distribution is therefore dominated by `EXPLICIT`, without relabeling
or modifying any v1/v2 artifact.

## No-claim rule

A no-claim result is valid only after all fourteen predicate families were checked. It
may coexist with ontology-gap records but not with assertions. No output can unlock a
predicate; `unlocked_predicates` remains empty outside this extraction payload.
