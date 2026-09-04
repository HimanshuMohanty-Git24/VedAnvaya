# Gold Annotation Protocol

Worksheet: [`data/gold/rigveda_semantic_gold_v1.jsonl`](../../data/gold/rigveda_semantic_gold_v1.jsonl)
Schema: [`schemas/semantic_gold_annotation.schema.json`](../../schemas/semantic_gold_annotation.schema.json)

120 rows, one per gold mantra, all currently `UNANNOTATED`. This is the human work the
semantic evaluation is blocked on, and it cannot be delegated to a model.

---

## Why a model may not write this

A gold set written by an LLM measures agreement between two model passes. That is not
precision, and it is worse than having no measurement, because it produces a number that
looks like one. Every acceptance decision in the layer is gated on this file; if it is
model-authored, the gate is the model checking itself.

---

## Filling in a row

Each line is one JSON object. Replace `annotator` and `annotated_at`, then fill
`entities` and `relations`.

```json
{
  "passage_key": "VG:RV:SAK:M06:S016:V019",
  "citation": "RV 6.16.19",
  "annotator": "your name or initials",
  "annotated_at": "2026-09-10T00:00:00Z",
  "entities": ["agniḥ", "soma"],
  "relations": [
    {"predicate": "INVOKES", "object_label": "agniḥ",
     "object_entity_key": "VG:DEVATA:AGNIH", "explicitness": "EXPLICIT",
     "note": "vocative ágne in pāda a"},
    {"predicate": "HAS_THEME", "object_label": "cosmic order",
     "object_node_type": "PHILOSOPHICAL_CONCEPT", "explicitness": "INTERPRETIVE",
     "rejected": true, "note": "nothing in the verse supports this; a reader primed by RV 10 would reach for it"}
  ],
  "notes": "",
  "schema_version": "1.0.0"
}
```

Rerunning `make semantic-config` **keeps** every row that has been edited and adds only
missing ones, so annotation can proceed incrementally without being overwritten.

---

## Rules for the annotator

1. **Annotate what the text supports, not what the hymn is famous for.** The pilot was
   selected by hash precisely to avoid the verses everyone already has an opinion about.
2. **Use only the evidence a packet would carry**: the Sanskrit, the morphology, the
   Griffith translation when it exists, the Anukramaṇī metadata, the lexical mentions,
   and the two neighbouring mantras. If you reach for Sāyaṇa or for a secondary source,
   the model was not given that and the comparison is unfair.
3. **Grade explicitness honestly and conservatively.** `EXPLICIT` means a reader can
   point at the words. If you need the English to make the claim, it is at best
   `STRONG_INFERENCE`.
4. **Record the tempting-and-wrong ones.** `rejected: true` is the most valuable field in
   the file. It is how the evaluation measures restraint rather than only recall, and it
   is the only way an over-reading is scored as a false positive instead of quietly
   ignored. Aim for at least one on any verse where a plausible over-reading exists.
5. **Do not try to be exhaustive.** A short, high-confidence annotation is more useful
   than a long speculative one: recall against an over-generous gold set punishes the
   model for declining, which is the behaviour we want.
6. **Do not restate the Anukramaṇī.** "This mantra is addressed to its assigned Devatā"
   is already an edge. It is not a semantic relation and the model is told not to emit
   one.
7. **Leave a `note` on anything you found difficult.** A disagreement between annotator
   and model is only informative if the annotator's reasoning is recoverable.

---

## When it is done

Any number of annotated rows is usable — the evaluator scores what exists and skips the
rest. But a predicate is unlocked for automatic acceptance only if its measured precision
reaches 95%, and a precision computed from three examples is not a measurement. Aim for
the full 120 before drawing conclusions about a predicate, and expect the low-frequency
predicates to remain locked simply for want of instances.
