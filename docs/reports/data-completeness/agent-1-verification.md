# Agent 1's gap census — lead verification

74 gaps: 62 IMPLEMENTATION_GAP, 7 STALE, 5 TRUE_SCOPE_FACT. The registry is well-formed —
all 74 `OPEN`, owners 3–16, 17 populations `null` with a stated reason, and the nine
`missing_count: 0` entries are the STALE findings where nothing is in fact missing, which
is a measured zero rather than an unknown.

This records what the lead re-measured. The rest is accepted on Agent 1's measurement and
marked as such.

## Confirmed — and this one corrects the campaign's own baseline

**The lemma layer reaches 39 words.**

```
MATCH (:Mantra)-[r:MENTIONS_LEMMA]->(l:Lemma)
RETURN count(r), count(DISTINCT l)     -> 9000 edges, 39 distinct lemmas

MATCH (l:Lemma) RETURN count(*), <isolated>   -> 10031 nodes, 9992 isolated (99.6%)
```

The 39 are all theonyms: `índra-` 2,305, `agní-` 1,604, `sóma-` 950, then `aśvín-`,
`marút-`, `váruṇa-`, `sū́rya-`, `uṣás-`, `pr̥thivī́-`, `mitrá-`, `savitár-`, `áditi-`.

`MENTIONS_LEMMA` is therefore a theonym mention index carrying a lemma layer's name. The
baseline's `Lemma | RV 6,560` is arithmetically exact and invites the reader to infer 62%
morphological coverage of the Rigveda. There is no morphology layer for any recension.

Worth stating plainly: this is the precise failure the campaign was convened to prevent — a
row where every figure is right and the meaning is wrong — and it was sitting in the
campaign's own frozen baseline, written by the lead, found by an independent census agent.
`BASELINE.md` now carries the warning beside the row rather than a corrected number,
because the number was never wrong.

**The gold set is an empty scaffold.**

| File | Rows | Annotator |
|---|---|---|
| `rigveda_semantic_gold_v1.jsonl` | 120 | `UNANNOTATED` × 120 |
| `theonym_mention_gold_v1.jsonl` | 575 | `MODEL_ADJUDICATED` × 575 |
| `ask_benchmark_v1.jsonl` | 60 | no annotator field |

Zero human annotations across 695 gold rows, and the only populated set was adjudicated by
claude-opus-5 — the same model family that produced much of what it would be scoring.
Section 26 forbids exactly that arrangement. Nothing in the product may currently be called
human gold.

## Confirmed, with a constraint Agent 1 stated and the lead is restating louder

**Samavedic audio is not source-blocked** — 475 inventory rows, every one found on
Wikimedia Commons, 459 CC BY-SA 4.0 and 16 CC0, `application/ogg`, and
`sha256_of_bytes: null` on all 475, so not one byte has been fetched.

Two properties in that inventory decide how Wave 1 must treat it:

| Field | Value |
|---|---|
| `alignment_granularity` | `PAGE_LEVEL` on all 475 |
| `gana_aligned` | `True` on 472, `False` on 3 |
| `sha1_is_not_sha256` | `True` on 475 |

So this material cannot close the Samaveda audio gap as it stands, for two independent
reasons, and conflating them would produce exactly the mapping the brief prohibits:

1. **Granularity.** Every file is aligned at page level, not verse level. Attaching one to
   a single Ārcika verse requires verified verse boundaries inside a page-length recording.
   Sections 9 and 22 are about precisely this, and an unverified boundary here would be a
   guessed timestamp.
2. **Identity.** These are *gāna* performances. The Ārcika text, the gāna text, the melodic
   notation and a recorded performance are four different objects, and sections 5 and 11
   forbid collapsing them. 1,844 Ārcika verses do not have 1,844 gāna recordings waiting
   for them; the relation between an Ārcika verse and a gāna rendering is itself an
   evidential claim needing source support.

The honest statement is that the Samaveda audio gap is no longer blocked on *finding*
material, and is now blocked on verse-boundary verification plus a separate gāna Work
identity. That is a better position than source-blocked, and it is not closure.

Someone previously recorded `sha1_is_not_sha256: True` against every row — Commons returns
SHA-1, which is not a content checksum under this campaign's contract. That was careful
work and it should be preserved.

## The STALE findings, and why they matter more than their count suggests

Seven claims in the product or its reports are contradicted by the graph. Two are served
live to users:

1. **`ATTRIBUTION-003`** — a live API caveat states the Atharvaveda carries no Anukramaṇī
   deity ascription. It carries 4,816 edges over 4,160 mantras. The lead independently
   confirmed the 4,160 figure while checking Agent 2's work, so two agents and the lead now
   agree the caveat is false.
2. **`MORPHOLOGY-003`** — the live Rigveda scope statement claims a Padapāṭha text version.
   All 44,276 `:TextVersion` nodes are `text_form='SAMHITA'`. Agent 2 reported the same
   thing independently as CORPUS_D05, so this is corroborated across both census agents.

The rest: `OTHER-005` (a report claims all four `Work.scope` properties are null; all four
are populated and served), `ATTRIBUTION-008` (`RishiFamily` reported as 0 nodes; it is 87
nodes, 305 edges, 302 seers resolved, so the real gap is 427 not 729), `COMMUNITIES-003`
(`CO_OCCURS_WITH` reported as 0; it is 306), `RITUAL-007` (aśvamedha reported absent; it is
one of the 8 modelled rites), `ENTITY_COVERAGE-005` (`trapu` reported unregistered;
`VG:CONCEPT:TRAPU-TIN` exists with 2 mentions).

A caveat that understates the data is not harmless. It tells a user a layer is missing when
it is present, and section 29 forbids removing a limitation card without proof — which
equally forbids *keeping* one that the data disproves.

## Two figures that do not reproduce

In both cases the live measurement is the more pessimistic, so nothing is understated:

- Benchmark Q67 claims 17 assertions carry three role slots. Measured: **0**, with 1,522
  carrying none. Agent 1 verified edge direction before counting, which is the step that
  makes this credible. It also found that `ASSERTION_AGENT` and `ASSERTION_TARGET` point
  only at `:Devata`, so a non-deity agent or target is not currently representable at all —
  a schema limit, not a data gap, and it constrains Agent 9's work.
- The scorecard says 30 of 33 GROUP deities lack components. Measured: **33 of 33**.

## Accepted on Agent 1's measurement alone

The remaining 62 registry entries, including: `MORPHOLOGY-005` (no mantra exists in both
scripts — RV and AV Latin-only, SV and YV Devanagari-only), `RITUAL-006` (no passage
carries a `ritual_context` property), `TRANSLATION-005` (every translation single-witness,
`alignment_confidence` null throughout), `AUDIO-005` (the whole audio layer proxied, with
`checksum`, `performer` and `licence` null on all 16,834 rows), `CROSS_VEDA-002` (zero of
6,527 reuse edges record a transformation type), and `SHARES_FORMULA_WITH` being the only
declared relationship type with zero edges.

Agent 1 counted every relationship type individually rather than reading the populated
census, which is why that last one is trustworthy: a census built from what exists cannot
report what is absent.
