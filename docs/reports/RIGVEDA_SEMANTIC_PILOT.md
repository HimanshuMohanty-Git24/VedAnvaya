# Rigveda Semantic Extraction Pilot

Pilot config: [`data/builds/rigveda_semantic_pilot_v1.yaml`](../../data/builds/rigveda_semantic_pilot_v1.yaml)
Config version: `rigveda-semantic-pilot-v1`
Selection rule: `rigveda-semantic-pilot-selection-v1`

**Status: the pipeline is built and tested end to end offline. The 508-mantra
Codex-direct pilot has completed.** Human gold remains the gate for promotion.

---

## What this layer is

The first place in VedaGraph where a language model is allowed to speak, and the only
one. It produces **candidate** assertions:

```
canonical corpus  ─┐
traditional layer  ├──> EvidencePacket ──> Luna ──> candidate ──> validator ──> policy ──> review
lexical layer     ─┘        (built                                                          │
                          without a model)                                                  ▼
                                                                                      accepted
```

Nothing in the chain writes back. The corpus, the 31,650 traditional assertions and the
9,000 lexical mention edges are inputs, opened read-only, and a run that modified one
would be a bug rather than a finding.

---

## Selection

508 mantras of 10,552 (4.8%), with a 120-mantra gold subset inside it. Selection is
deterministic: the same corpus produces the same pilot, and the config is a meaningful
diff.

Ordering **within** a stratum is by a hash of the passage key, not by citation. Taking
the first *n* by citation would fill the pilot with RV 1.1–1.20 and Maṇḍala 10's opening
hymns — the most translated, most quoted, most memorised verses in the corpus, and
therefore the ones a model is most likely to reproduce from training rather than read
from the packet. Precision measured there would flatter the extractor and say nothing
about the other ten thousand mantras.

| stratum | pilot | gold | why it is in the pilot |
|---|---:|---:|---|
| `TRANSLATION_MISSING` | 52 | 1 | no Griffith verse exists; the model must decline rather than translate |
| `LEXICALLY_AMBIGUOUS` | 45 | 10 | the lexical layer deliberately refused to resolve a token here |
| `EXACT_PARALLEL` | 45 | 4 | recurs verbatim elsewhere, so two extractions can be compared |
| `NEAR_PARALLEL` | 30 | 0 | similar wording, possibly different claims |
| `RARE_DEVATA` | 40 | 10 | a Devatā with ≤ 12 mantras: thinnest registry coverage |
| `RARE_CHANDAS` | 25 | 0 | a metre with ≤ 12 mantras |
| `RARE_RISHI` | 25 | 13 | a Ṛṣi with ≤ 12 mantras |
| `MULTI_DEVATA` | 6 | 0 | tradition assigns more than one Devatā |
| `NO_LEXICAL_MENTION` | 40 | 40 | no deterministic mention: no entity to lean on |
| `SHORT_SUKTA` | 25 | 0 | a Sūkta of ≤ 3 mantras: little context |
| `LONG_SUKTA` | 25 | 6 | a Sūkta of ≥ 30 mantras: a narrow window |
| `MANDALA_09_SOMA` | 40 | 3 | Maṇḍala 9 is almost all Soma Pavamāna: highly repetitive |
| `MANDALA_10` | 40 | 5 | cosmological and philosophical material |
| `MANDALA_SPREAD` | 70 | 28 | an even draw so no book appears only through its hard cases |
| **total** | **508** | **120** | |

`MULTI_DEVATA` filled 6 of a 25 quota because the whole corpus contains exactly six
mantras with more than one `HAS_DEVATA` — the Anukramaṇī records composite deities
(`mitrāvaruṇau`, `indrāgnī`) as single entities, so double assignment is rare. All six
are in the pilot. The shortfall is a fact about the source, not a selection bug, and the
quota is left visible rather than back-filled with something else.

Per Maṇḍala:

| M | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pilot | 89 | 16 | 20 | 23 | 27 | 28 | 37 | 64 | 78 | 126 |
| gold | 23 | 2 | 2 | 7 | 10 | 9 | 8 | 26 | 15 | 18 |

Every Maṇḍala is represented in both, and a test asserts it.

---

## The evidence packet

One request sees: the mantra's canonical id and citation, its Sanskrit
(`GRETIL.RV.AUFRECHT`), the Griffith translation when one exists, its Ṛṣi / Devatā /
Chandas, every annotated token with lemma and morphology, every deterministic lexical
mention, the previous and next mantra, the Sūkta's length, and the ids of any exact or
near parallels.

Three limits are deliberate.

**Window.** Previous, target, next. Sūkta context is supplied as counts and identifiers,
not text. A whole Maṇḍala per request would cost roughly two orders of magnitude more
per mantra and make every assertion unfalsifiable, because enough text supports anything.

**No generated translation.** 52 pilot mantras have no Griffith verse. Those packets set
`translation_missing` and carry Sanskrit and morphology alone, and the prompt tells the
model to emit fewer assertions rather than translate. Asking it to translate would put a
model-authored English sentence into the evidence chain for every later claim, and the
provenance would then be the model citing itself.

**Parallels are named, not resolved.** An exact parallel is supplied as an identifier so
the model knows the line recurs. It is not a licence to copy an assertion across. Whether
the two extractions agree is measured afterwards, and disagreement is a signal about the
extractor rather than about the text.

Every packet carries `input_sha256`, a hash of exactly what was sent. **That is the
entire reproducibility claim of this layer.** Two runs with the same hash saw the same
evidence. Nothing about the model's reply is reproducible in the sense the canonical
corpus builds are, and no report here says otherwise.

---

## What stops a bad assertion

In order, and each is a separate failure mode:

| check | catches |
|---|---|
| strict Structured Outputs | a predicate or node type outside the ontology; a malformed reply |
| `PASSAGE_NOT_IN_PACKET` | a claim about a mantra the model was not shown |
| `PREDICATE_FORBIDDEN` | `SYMBOLIZES`, `REPRESENTS`, `IS_GOD_OF`, `MEANS`, `CAUSES` |
| `OBJECT_TYPE_INVALID` | `REFERS_TO_PLACE` pointing at an offering |
| `UNKNOWN_CANONICAL_ENTITY` | a deity that is not in the registry |
| `NO_EVIDENCE` | an assertion with nothing under it |
| `EVIDENCE_TOKEN_NOT_IN_PASSAGE` | **a fabricated citation** — the model named a token it was never shown |
| `EVIDENCE_TRANSLATION_NOT_SUPPLIED` | a translation id that was not in the packet |
| `EXPLICITNESS_UNSUPPORTED_BY_EVIDENCE` | `EXPLICIT` resting on the English alone |
| `DETERMINISTIC_CONTEXT_CONFLICT` | address claims that diverge from the Anukramaṇī — flagged, never rejected |

The token check is the most valuable one in the layer. It is the difference between "the
model produced a claim I cannot verify" and "the model produced a claim it invented the
evidence for", and it is decidable.

---

## Duplicate concept control

The failure mode that ruins semantic knowledge graphs is *Creation*, *Cosmic Creation*,
*Creation of the Universe*, *Cosmogony* and *Origin of the Cosmos* becoming five nodes
with a fifth of the evidence each. Nothing downstream recovers from it, because by then
the graph looks populated.

The rule is **exact identity may merge; similarity may only ask**:

- a proposal whose normalized label or reviewed alias hits a registry row **is** that row;
- a proposal that merely *looks like* one becomes a review candidate carrying both labels
  and creates nothing;
- a concept proposed from a single mantra is `NEEDS_REVIEW`, not a new entity — one
  occurrence is usually a phrasing;
- no embedding similarity is used in this phase, in either direction.

Character similarity appears once, as a brake: it withholds automatic creation and fills
a normalization queue. `Cosmic Order` and `Ṛta` may well be one entity; they may also be
a Vedic term and a translator's gloss of it, and string distance does not settle that.

---

## What a run writes

Under `data/semantic/<run_id>/`, gitignored. Identifiers and hashes only — no Sanskrit,
no translation text, no raw model payloads:

| file | contents |
|---|---|
| `semantic_candidates.jsonl` | every candidate assertion with its status |
| `semantic_entities_candidates.jsonl` | proposed concepts with their registry resolution |
| `semantic_validation.jsonl` | one verdict per candidate, with codes and reason |
| `accepted_semantic_assertions.jsonl` | `AUTO_ACCEPTED` only |
| `review_semantic_assertions.jsonl` | `NEEDS_REVIEW` |
| `rejected_semantic_assertions.jsonl` | `VALIDATION_REJECTED` |
| `parse_errors.jsonl` | schema-conformant replies holding a claim that could not be built |
| `normalization_queue.jsonl` | candidate concepts a person should adjudicate as duplicates |
| `evidence_packet_index.jsonl` | what was sent, as ids and hashes |
| `semantic_run_manifest.json` | model, effort, versions, pinned corpus hashes, usage |
| `token_usage.json`, `cost_report.json` | actual API usage and what it cost |

A claim that cannot be built is dropped and its reason recorded. It is never repaired by
guessing what the model meant: that is how an unsupported assertion enters the graph
wearing a validator's approval.

---

## Remaining gate

The gold subset is not annotated. `data/gold/rigveda_semantic_gold_v1.jsonl`
holds 120 rows, all marked `UNANNOTATED`. Gold must be written by a person: an
LLM-authored gold set would measure agreement between two model passes, which is not
precision and would be worse than no measurement because it would look like one. The
evaluator skips `UNANNOTATED` rows rather than scoring them as "no relations here", which
would manufacture a precision of zero out of an empty file.

Until the gold set exists, `unlocked_predicates` is empty, and the Codex-direct run routes
**every** clean candidate to human review and auto-accepts nothing. That is a usable
state — it produces reviewable candidates with checked evidence — but it is not the
state a full-corpus run should be authorised from.

---

## Readiness

**`READY_WITH_LIMITATIONS`.** The pipeline is complete, typed, linted and tested offline,
and it refuses to accept anything it has not been given grounds to accept. It has not
been measured, and the parts that need measuring are exactly the parts that need an API
key and a human annotator.

Full-corpus extraction is **not** authorised by this document and must not be run from it.
