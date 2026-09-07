# Rigveda semantic gold reviewer guide

The gold label is human judgment from the EvidencePacket. It is not approval of Luna.
Run `uv run vedagraph semantic gold review`; Stage A is blinded and shows only packet
evidence. Finish and save a row before using `M` to reveal any model suggestion.

Evidence labels have epistemic meaning:

- `[TEXT]` is the local Sanskrit passage.
- `[GRIFFITH TRANSLATION]` is supplied English and may be absent.
- `[TRADITIONAL METADATA]` is deterministic Anukramaṇī material; Devatā assignment is
  not proof that the mantra semantically invokes or praises that entity.
- `[LEXICAL DETERMINISTIC]` and `[MORPHOLOGY DETERMINISTIC]` are token-level records.
- `[PARALLEL DETERMINISTIC]` names a parallel but does not copy its interpretation.

Annotate zero or more entities and relations. Use `N` when the packet supports no
semantic assertion. Add a relation even when Luna emitted nothing; that is how recall
is measured. If a desired type or relation is absent from the ontology, record an
`ONTOLOGY_GAP` rather than inventing a value.

Explicitness examples (invented, not corpus labels):

- `EXPLICIT`: “O Dawn, come here” with a token or supplied translation that names Dawn
  and a direct imperative/vocative. A reader can point to the words.
- `STRONG_INFERENCE`: “May we have safety” when the wording clearly requests safety,
  but the grammatical relation requires a small, defensible inference from the verse.
- `INTERPRETIVE`: assigning “cosmic order” as a theme because the passage feels
  cosmological, without a phrase or tightly linked evidence that supports it.

Choose no claim when the only support is tradition, a vague association, an outside
commentary, a model suggestion, or a translation gloss that cannot be anchored to the
packet. Record a rejected tempting relation when it captures a plausible over-reading;
this measures restraint.

For every accepted entity/relation, select deterministic evidence IDs from the displayed
packet. Do not copy source text into the JSONL. The validator rejects token,
translation, passage, entity, traditional-assertion, and parallel IDs that are not
actually present.

Workflow commands:

`A` add supported assertion · `R` add rejected tempting relation · `E` add entity ·
`O` record ontology gap · `D` edit · `N` no claim · `S` save in progress ·
`C` or Enter complete and advance · `X` needs second review · `K` skip temporarily ·
`P` previous · `J` jump · `M` reveal model after Stage A lock · `Q` save and quit.

If Stage A is edited after model reveal, give a reason. Such rows are retained and
flagged as `gold_modified_after_model_reveal`; they remain identifiable in evaluation.
Run `uv run vedagraph semantic gold validate` before finalization, then
`uv run vedagraph semantic gold finalize` only after the human review is actually done.
