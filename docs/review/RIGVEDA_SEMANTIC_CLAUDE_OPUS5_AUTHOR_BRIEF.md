# Author brief — Rigveda semantic candidate authoring, Claude Opus 5 / V3.2 / 448

**NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.**
**CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
**ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**

You are authoring semantic candidates for **exactly one** Rigveda passage. Every one of
the 448 author contexts in this run reads this same brief, unchanged. Do not adapt it.

Run: `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`
Provenance bucket: `CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION`

---

## 1. Isolation rules — read these first

You may read **only**:

- `prompts/semantic_extraction_v3.2.md` — the frozen extraction policy. It is the
  authority on what to emit. This brief is the mechanical format only.
- the output of `python scripts/claude448.py render <PASSAGE_ID>` — your EvidencePacket.
- this brief.

You must **not** read, search, grep, glob or open:

- any other passage's packet or output,
- any file under `data/semantic/` (use `render`, never the raw directories),
- any file under `docs/reports/`,
- any `author_inputs/` directory or file other than the one you write,
- any historical Luna, Sol, heuristic, regression, stability or comparison artefact,
- any earlier attempt at your passage. One exists for some passages and it is classified
  `UNTRUSTED_ABANDONED_AUTHOR_INPUT`. It is not an answer, not a hint and not a target.

Do not use remembered Vedic knowledge. The EvidencePacket is your only evidence. A claim
you can support only from tradition, scholarship or memory is not emittable here.

There is no density target. Do not try to match any other passage, any other run, or any
number you may have seen. Emit exactly what the packet supports — no more, no less.

---

## 2. What to do

1. Read `prompts/semantic_extraction_v3.2.md` in full.
2. Run `python scripts/claude448.py render <PASSAGE_ID>` and read the packet.
3. Inspect **all fourteen** predicate families in the prompt's order. It is a checklist,
   not a quota: a family that fails the test contributes nothing.
4. Write your intermediate JSON to the output path you were given.
5. Run `python scripts/claude448.py check <PASSAGE_ID> <YOUR_FILE>`.
6. If `status` is `REJECTED`, fix the **format** problem it names and re-check. Never
   weaken a semantic judgement to make a validator pass; if a relation genuinely cannot be
   anchored to specific wording, that relation is not emittable — drop it.
7. Stop when `status` is `OK`.

---

## 3. Intermediate JSON format

You author semantics only. Offsets, candidate IDs, assertion IDs, receipts and hashes are
minted mechanically from your quotes — never write them yourself.

```json
{
  "no_claim": false,
  "no_claim_reasons": [],
  "assertions": [
    {
      "predicate": "REQUESTS",
      "explicitness": "EXPLICIT",
      "inference_step": null,
      "relation_quote": "May he",
      "relation_occurrence": 1,
      "object": {
        "object_kind": "REQUESTED_OUTCOME",
        "display_label": "standing by the worshippers in need and in abundance",
        "normalized_head": "stand by us",
        "object_quote": "stand by us in our need and in abundance for our wealth",
        "object_occurrence": null,
        "canonical_entity_id": null,
        "target_entity_id": null,
        "beneficiary_entity_id": null,
        "event": null,
        "ontology_gap_code": null,
        "qualifiers": []
      }
    }
  ]
}
```

A no-claim result is:

```json
{"no_claim": true, "no_claim_reasons": ["<which family or boundary failed, invent no semantics>"]}
```

`no_claim` may not coexist with assertions.

### Field rules

| Field | Rule |
|---|---|
| `predicate` | One of the fourteen allowed families. Never `SYMBOLIZES`, `REPRESENTS`, `IS_GOD_OF`, `MEANS`, `CAUSES` — including hidden inside `ASSOCIATED_WITH`. |
| `explicitness` | `EXPLICIT` or `STRONG_INFERENCE` only. `INTERPRETIVE` is prohibited: if it would be interpretive, do not emit. |
| `inference_step` | Required and non-empty when `explicitness` is `STRONG_INFERENCE`; name the single limited inferential step. Otherwise `null`. |
| `relation_quote` | An **exact substring** of `translation.text` carrying the relation force. |
| `object_quote` | An **exact substring** of `translation.text` identifying the target/object. |
| `*_occurrence` | 1-based. Required when the quote appears more than once; omit or `null` when unique. |
| `display_label` | Concise human annotation. Not identity. Not the whole sentence. |
| `normalized_head` | Concise comparison head. **Required** for every kind except `CANONICAL_ENTITY_REF` and `ONTOLOGY_GAP_REF`. Not a global concept ID. |
| `canonical_entity_id` | **Only** for `CANONICAL_ENTITY_REF`, and **required** there. Must be an `entity_key` from `lexical_mentions` in your packet. A `traditional_devata_keys` value is *not* usable unless it also appears in `lexical_mentions`. |
| `target_entity_id`, `beneficiary_entity_id` | `null`, or an `entity_key` from `lexical_mentions`. |
| `event` | **Only** for `object_kind: "EVENT"`, and **required** there: `{"action_head": "...", "actor_entity_id": null, "patient_entity_id": null, "other_participants": [], "qualifiers": []}`. Entity IDs must be supplied lexical mentions or `null`. Each entry in `other_participants` needs `role` plus exactly one of `entity_id` / `normalized_head`. |
| `ontology_gap_code` | **Only** for `ONTOLOGY_GAP_REF`, and **required** there: one of `PERSON_LIKE_REFERENT_UNMODELED`, `PATRON_ROLE_UNMODELED`, `ANCESTOR_ROLE_UNMODELED`, `KINSHIP_ROLE_UNMODELED`, `OTHER_UNMODELED`. |
| `qualifiers` | List of short strings, or `[]`. |

### Anchoring rules (these cause most rejections)

- A quote must match `translation.text` **character for character**, including
  punctuation and diacritics. Copy it; do not retype it.
- A quote must be **boundary-safe**: it may not begin or end inside a word. `rais` inside
  `praise` is rejected. Quote whole words.
- The relation anchor and the target/outcome anchor of one assertion may **not** be the
  identical span. Quote the relation wording and the object wording separately.
- A span covering the **whole verse** is not assertion-specific evidence and is rejected.
- `REQUESTS` needs its `object_quote` on the **requested outcome itself**.
- `INVOKES`, `PRAISES` and `DESCRIBES` with a `CANONICAL_ENTITY_REF` object need the
  `object_quote` to be the wording that **names or addresses that entity**. A name
  occurring elsewhere in the verse is not an address.

### Predicate → object-kind table

| Predicate | Preferred kind | Also allowed (review-only) |
|---|---|---|
| `INVOKES` | `CANONICAL_ENTITY_REF` | `OPAQUE_REFERENT`, `ONTOLOGY_GAP_REF` |
| `PRAISES` | `CANONICAL_ENTITY_REF` | `SEMANTIC_ENTITY_REF`, `OPAQUE_REFERENT`, `ONTOLOGY_GAP_REF` |
| `DESCRIBES` | `CANONICAL_ENTITY_REF`, `SEMANTIC_ENTITY_REF` | `OPAQUE_REFERENT`, `ONTOLOGY_GAP_REF` |
| `REQUESTS` | `REQUESTED_OUTCOME` | `OPAQUE_REFERENT`, `ONTOLOGY_GAP_REF` |
| `DESCRIBES_ACTION` | `EVENT` | `ACTION_REF`, `OPAQUE_REFERENT` |
| `INVOLVES_RITUAL` | `RITUAL_EVENT` | `OPAQUE_REFERENT` |
| `INVOLVES_OFFERING` | `OFFERING_REF` | `OPAQUE_REFERENT` |
| `INVOLVES_SUBSTANCE` | `SUBSTANCE_REF` | `OPAQUE_REFERENT` |
| `REFERS_TO_NATURAL_PHENOMENON` | `NATURAL_PHENOMENON_REF` | `OPAQUE_REFERENT` |
| `REFERS_TO_PLACE` | `PLACE_REF` | `OPAQUE_SPATIAL_REFERENT`, `OPAQUE_REFERENT` |
| `EXPRESSES` | `STATE_REF`, `QUALITY_REF`, `CONCEPT_REF`, `SEMANTIC_ENTITY_REF` | `OPAQUE_REFERENT` |
| `HAS_THEME` | `CONCEPT_REF` | `OPAQUE_REFERENT` |
| `ASSOCIATED_WITH` | — | any kind (review-sensitive) |
| `CONTRASTS_WITH` | — | any kind (review-sensitive) |

---

## 4. What you return

Return **only** a single-line JSON object and nothing else:

```json
{"passage_id":"...","group":"...","status":"OK","assertions":3,"no_claim":false,"check_attempts":1,"notes":""}
```

Set `"status":"BLOCKED"` with a short `notes` only if you cannot reach `OK` — say what
the validator rejected. Do not paste your semantic output into the reply; it is already
on disk. Do not summarise the passage.
