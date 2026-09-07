# Reviewer brief — bounded engineering-support audit, Claude Opus 5 / V3.2 / 448

**NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.**
**CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
**ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**

You are adjudicating **engineering support** for the model-authored assertions of exactly
one passage from the sealed run. You are not a Vedic scholar of record, you are not
producing gold, and your verdict is never precision. The only thing your output may ever
be called is a **model-adjudicated engineering support rate**.

---

## 1. What you may read

- the EvidencePacket: `python scripts/claude448.py render <PASSAGE_ID>`
- the frozen policy: `prompts/semantic_extraction_v3.2.md`
- the passage's authored output, which you will be given inline
- this brief

Do **not** read any other passage, any other author's output, any historical Luna, Sol or
heuristic artefact, or any file under `docs/reports/`. Do not use remembered Vedic
knowledge, traditional commentary, or scholarship. **The author's output is not evidence
that the author was right.** Start from the packet, not from the assertion.

---

## 2. What you decide, per assertion

Classify each assertion into exactly one category:

| Category | Meaning |
|---|---|
| `DIRECTLY_SUPPORTED` | The packet directly supports both the relation force and the bound target/object. The anchors point at the right wording. |
| `SUPPORTED_BUT_REDUNDANT` | Supported, but says the same thing as another assertion in the same passage — a duplicate in substance, not an independent relation. |
| `PREDICATE_AMBIGUOUS` | The content is supported but the predicate family is genuinely arguable (e.g. `DESCRIBES` vs `DESCRIBES_ACTION`, `EXPRESSES` vs `HAS_THEME`). |
| `OBJECT_GRANULARITY_AMBIGUOUS` | Supported, but a reasonable reader would split or merge the object differently (most often `REQUESTS` outcome splitting). |
| `WEAK_SUPPORT` | The relation is only reachable by a stretch — more than the one limited inferential step `STRONG_INFERENCE` permits. |
| `UNSUPPORTED` | The packet does not support this relation or this target at all, or the anchor points at wording that does not carry the claim. |
| `EXPERT_REQUIRED` | Resolving it genuinely needs a Vedicist. Use this rather than guessing. |

`UNSUPPORTED` is the serious one. Reserve it for a claim the evidence does not carry —
including a canonical target bound to the wrong entity, or an anchor whose wording does
not express the relation asserted. Ambiguity is not unsupported.

Also flag, separately from the category:

- `fabricated_evidence`: true if any anchor quotes wording that is not in the packet, or
  points at wording that has nothing to do with the assertion.
- `wrong_entity_binding`: true if a `canonical_entity_id` names an entity the anchored
  wording does not identify or address.

These two are the failure modes that would block a freeze. Be strict about them and
conservative about everything else.

---

## 3. What you return

Return only the structured object you were asked for. Per assertion give the
`assertion_id`, the category, a one-sentence reason grounded in the packet wording, and
the two boolean flags. Add a one-line `passage_note` only if something about the passage
as a whole matters. Do not restate the verse, do not summarise, do not propose rewrites —
nothing here edits model output.
