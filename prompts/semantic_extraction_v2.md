---
prompt_version: rigveda-semantic-extraction-v2
ontology_version: rigveda-semantic-ontology-v1
packet_version: rigveda-semantic-evidence-packet-v1
---

# Rigveda semantic extraction — predicate-family checklist v2

Return only the structured object required by the extraction schema. Every item is a
candidate for review, never an accepted graph edge. Use only this EvidencePacket:
Sanskrit, supplied morphology/tokens, Griffith's supplied translation, deterministic
traditional metadata, deterministic lexical mentions, neighbouring passage context,
and deterministic parallel identifiers. Do not use remembered Vedic knowledge.

Before deciding whether the assertion list is empty, independently check every allowed
predicate family below. The checklist is an internal trace and is not itself an
assertion. A family marked NOT_SUPPORTED or UNCERTAIN produces no assertion.

1. INVOKES — direct address, call, summons, invitation, or appeal to an entity.
2. PRAISES — explicit laudation, celebration, extolling, magnifying, or honoring.
3. REQUESTS — an explicit desired result such as protection, wealth, health, presence,
   assistance, release, food, victory, offspring, or long life. Keep this distinct from
   INVOKES; one passage can support both.
4. DESCRIBES — an explicit property, state, role, form, or condition of an entity.
5. DESCRIBES_ACTION — an expressed action or event; use a short reusable action label.
6. INVOLVES_RITUAL — an explicit ritual act or ritual context.
7. INVOLVES_OFFERING — an offering explicitly presented, poured, prepared, sacrificed,
   or given. Keep this distinct from the material SUBSTANCE.
8. INVOLVES_SUBSTANCE — an explicitly named material or substance, whether offered or
   not. Keep this distinct from the offering act.
9. REFERS_TO_NATURAL_PHENOMENON — an explicit natural phenomenon, not deity identity
   or metaphor alone.
10. REFERS_TO_PLACE — an explicit spatial location or place; do not promote every seat,
    dwelling, or metaphorical location to PLACE.
11. EXPRESSES — explicit desire, fear, yearning, attitude, intention, or state content.
12. HAS_THEME — a conservative broad reusable theme, only when the passage/context
    strongly supports it and it is broader than one object or action.
13. ASSOCIATED_WITH — only an explicit association not better represented above.
14. CONTRASTS_WITH — two entities/states/concepts explicitly set against each other.

Use EXPLICIT only when the supplied words directly carry the claim. Use
STRONG_INFERENCE when the claim is entailed mainly by a supplied translation or by a
clear combination of evidence. INTERPRETIVE is exceptional. Cite valid packet ids and
token ids; never invent evidence references.

Existing Devata, Rishi, and Chandas entities must be referenced by their supplied
canonical keys. New semantic objects may be proposed as SemanticEntity candidates only
for short reusable labels such as protection, Soma pressing, offering, a substance,
an action, a state, a natural phenomenon, or a place explicitly present in the packet.
Do not mint canonical ids, merge SOMA with PAVAMANA SOMA, or force human/person/opaque
referents into another ontology type. Record an ONTOLOGY_GAP in uncertainties when the
ontology cannot represent a supported referent.

Never emit forbidden predicates such as IS_GOD_OF, SYMBOLIZES, REPRESENTS, MEANS, or
CAUSES, including indirectly through ASSOCIATED_WITH. Traditional HAS_DEVATA metadata
is context and never by itself supports INVOKES or PRAISES. A no-claim is valid only
after all fourteen families were checked.
