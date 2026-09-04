# Rigveda Semantic Extraction Cost

Model: `gpt-5.6-luna` (OpenAI Responses API, strict Structured Outputs)

**No live run has taken place, so every figure here is an estimate and is labelled one.**
The pipeline records the API's own `usage` object on every reply and never substitutes an
estimate when a real number exists; the moment a live run happens, `cost_report.json`
replaces this page's numbers with measured ones.

---

## Published rates

| | USD per million tokens |
|---|---:|
| input | 0.20 |
| cached input | 0.02 |
| output | 1.20 |

Pinned in `ExtractionConfig` and recorded on every run manifest, so a later price change
does not silently rewrite an old run's cost.

---

## Measured: packet size

This part is **not** an estimate. Every one of the 508 pilot packets was built and
serialised locally by `make semantic-dry-run`:

| | value |
|---|---:|
| packets built | 508 |
| packets with no Griffith translation | 52 |
| total request characters (system prompt + packet) | ~6.89 million |
| **estimated input tokens** (at ~3.6 chars/token) | **1,914,941** |
| average per request | ~3,770 |

The token figure is derived from an exact character count at an assumed ~3.6 chars per
token. The character count is measured; the tokens-per-character ratio is not.

---

## Estimated: a pilot run

Output size is the unknown. 900 tokens per reply is a planning assumption — enough for a
handful of assertions with evidence and a short uncertainty list — and a live run
replaces it with the API's figure.

| | value |
|---|---:|
| requests | 508 |
| input tokens (estimated) | 1,914,941 |
| output tokens (assumed 900/reply) | 457,200 |
| input cost | $0.383 |
| output cost | $0.549 |
| **estimated pilot cost** | **$0.93** |
| estimated cost per mantra | $0.0018 |

No prompt caching is assumed. The system prompt is identical across all 508 requests and
is a substantial share of each one, so a real run will likely see cached input tokens
billed at a tenth of the rate — the estimate above is therefore more likely high than low
on the input side.

---

## Projected: the full Rigveda

At the pilot's per-mantra rate, 10,552 mantras:

| | value |
|---|---:|
| **projected full-corpus cost** | **~$19.35** |
| via the Batch API (50% discount, if applicable) | ~$9.70 |

This is a **projection from an estimate**, not a measurement, and it carries two
assumptions worth stating:

1. The pilot is deliberately stratified towards awkward mantras — missing translations,
   long Sūktas, rare deities — so its per-mantra input size is more likely above the
   corpus average than below it. The projection is therefore more likely high.
2. Output size is assumed, not observed. If replies run to 2,000 tokens rather than 900,
   the full-corpus figure roughly doubles to ~$32.

Either way the conclusion is the same and it is worth stating plainly: **cost is not the
constraint on this project.** Twenty dollars does not decide whether to run the full
Rigveda through a model. Precision does. A cheap run that puts eleven thousand
unverifiable edges into a knowledge graph is expensive in the only currency that matters
here, which is whether anyone can trust the result.

---

## What a live run records

`data/semantic/<run_id>/cost_report.json`, from the API's own usage numbers:

- total input, cached-input, output and reasoning tokens
- request count, and average input/output per request
- total cost, cost per mantra
- projected full-corpus cost, explicitly labelled a projection

`semantic_run_manifest.json` records alongside it the model string the API returned, the
reasoning effort, `max_output_tokens`, the prompt version, the ontology version, the
packet version and the pinned corpus hashes.

`gpt-5.6-luna` publishes no dated snapshot, so the model id *is* the pin. The manifest
records the model string the API returned as the only version evidence available, and no
report claims more reproducibility than that.
