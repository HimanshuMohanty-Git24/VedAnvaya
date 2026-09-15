# Wave 3 — canonical integration plan

Owner section R item 5. **Nothing here has been executed.** The graph stands at 108,779
nodes and 265,295 relationships and no canonical write has occurred in this campaign.

Four of eight Wave 2 agents have reported. This plan covers what exists now and is
provisional on the remaining four (11 semantic resemblance, 13 ritual, 14 scholarship,
16 quality).

## What is staged

Ten domains, all passing `validate_staging_artifact.py --graph` at 100% evaluation coverage.

| Domain | Rows | Strong | Weak | Rejected | Unresolved |
|---|--:|--:|--:|--:|--:|
| translation | 2,254 | 1,514 | 740 | 673 | 0 |
| audio_rv | 150 | 150 | 0 | 750 | 0 |
| audio_yv | 33 | 25 | 8 | 201 | 0 |
| audio_av | 771 | 764 | 7 | 191 | 197 |
| samaveda_music | 1,471 | 1,471 | 0 | 16 | 708 |
| attribution | 23,003 | 23,003 | 0 | 18 | 16 |
| formula | 5,636 | 5,636 | 0 | 14,574 | 0 |
| communities | 1,028 | 1,028 | 0 | 57 | 324 |
| cross_veda | 7,021 | 7,021 | 0 | 13,074 | 115 |
| semantic_roles | 14,235 | 14,235 | 0 | 5,965 | 10 |
| **Total** | **55,602** | **54,847** | **755** | | |

"Strong" is `EXACT` or `VERIFIED_SEGMENT`. "Weak" is `PROBABLE` or `UNVERIFIED`, which the
validator already treats as staged-and-not-importable.

**These are not import counts.** Three gates and four schema prerequisites sit between this
table and the database, and they reduce it considerably.

## Gates that are currently CLOSED

| Gate | Scope | State |
|---|---|---|
| Owner decision E — listening review | all 939 new audio rows, plus the 61 in the RV span | **CLOSED.** 1,021 rows queued in `audio_review_queue.jsonl`, all `NEEDS_AUDIBLE_REVIEW`, 0 reviewed. |
| Owner decision A — RV 1.65–1.70 | 61 canonical keys, all domains | **CLOSED** until the coordinate repair is verified and applied. |
| Owner decision C — forced addresses | 31 Yajurvedic translation rows | **CLOSED** permanently unless independent content verification arrives. |

Recorded in `data/staging/lead_overlays/wave1_decisions.json`. The import must read overlays
after artifacts and apply them, or it will import rows the owner has barred.

## Schema prerequisites — additive, and four of them block their own domain

None of these renames or re-points an existing predicate. Each must land *before* its
domain's rows, because the rows have nowhere to go otherwise.

1. **`:RoleFiller` + `ASSERTION_ROLE` + `ROLE_FILLER_ENTITY`** — blocks most of
   `semantic_roles`. `ASSERTION_AGENT` and `ASSERTION_TARGET` point only at `:Devata`, so
   91.9% of role fillers cannot be attached. The graph already pays this: 1,364 patients,
   366 instruments, 356 beneficiaries and 225 locations are stored as opaque strings with
   zero edges. Verified. Proposal staged by Agent 9 with all 118 referenced entity keys
   resolved live.
2. **A home for the running Saṃhitā number** — blocks `MUSICALIZED_AS`. It is the only key
   joining an Ārcika verse to a gāna rendering and it exists nowhere in the graph, so the
   495 edges could not be re-derived after import. `GAP-SAMAVEDA_MUSIC-003`.
3. **Four gāna `Work` identities** — Grāmageyagāna, Āraṇyageyagāna, Ūhagāna, Ūhyagāna, each
   with a deterministic URN and UUIDv5 from namespace `7c8cde94-2bc0-50e2-8819-568ae65a3ec4`.
   Staged `PROPOSED_FOR_LEAD_ADJUDICATION`. Rahasyagāna deliberately not modelled, because
   folding it into Ūhyagāna and minting a fifth Work each assert something unsettled.
4. **`MUSICALIZED_AS` range widening** — currently glossed RV→SV, and it must carry SV→gāna.

Also additive but not blocking: a `polarity` field on assertions (2,061 assertions sit
inside a negation's scope and are only flagged), and `role_derivation`.

## Order of operations

The ordering is not preference. Each step's output is the next step's input, and two steps
would destroy evidence if run late.

**Phase 0 — repair before recovery.**
Apply the RV 1.65–1.70 re-binding from `data/staging/rv_coordinate_repair/`: unit *k* to
verses *2k−1* and *2k*, with `PAIR_SCOPE` declared, verified per verse rather than by
formula. Then lift the decision-A bar. *Nothing may be written into those six hymns first* —
filling them would leave every verse carrying text and 25 carrying the wrong text.

**Phase 1 — schema extensions.** The four above, each with a migration note and a rollback.

**Phase 2 — corrections to existing data, before additions.**
These fix what is already wrong, and every one of them changes counts that later phases
would otherwise inherit:
- The 1,903 Yajurvedic translations citing a `:Source` that does not exist
  (`SACRED_TEXTS`), with `GRIFFITH_WHITE_YAJURVEDA` referenced by nothing.
- `occurrence_count`: null on all 214 `:Devata` and 575 `:Chandas`, and written to two
  incompatible conventions on `:Rishi` with all 367 Rigveda-only seers at 0. One contract,
  applied last, raising on an unrecognised label.
- `attribution_scope: ["RV"]` on all 214 `:Devata` — derive it from the graph instead of
  storing a literal that outlives its fact.
- The AV `SEARCH_DERIVATIVE` layer, which deletes base letters across 5,839 mantras.
- 4,368 parallel typology backfills and the `ParallelMethod`→`MatchLevel` mapping for the
  256 edges that already carry their evidence under another property name.
- The 1,684 `REUSES_TEXT_FROM` edges mislabelled `evidence_basis: SANSKRIT` for a direction
  that rests on the tradition's self-description, not on measurement.

**Phase 3 — additions, largest and least contentious first.**
`attribution` (23,003), `semantic_roles` (14,235, after phase 1), `cross_veda` (7,021),
`formula` (5,636), `samaveda_music` notation (1,136, after phase 1), `translation` (1,514
minus the 31 barred minus the RV span until phase 0 clears).

**Phase 4 — audio, only when the listening gate opens.** 939 strong rows. Not before.

**Phase 5 — `communities`: do not import as fact.**
Agent 15 computed the partition and refused publication, on evidence: six of twelve
communities draw every internal edge from a single hymn, five are whole connected
components, and every method separates Bṛhaspati from Brahmaṇaspati. Import the
**artifact** with its method metadata and its refusal, not a membership claim. The existing
typed refusal on the product surface is more accurate than this partition presented as a
result.

**Phase 6 — dependent rebuilds (section 33).** After the additions, re-run: entity mention
detection, formula discovery, semantic resemblance, cross-Veda analysis, the Ask search
index, coverage metrics, visualisation aggregates. Stale relations computed over partial
data are worse than absent ones.

## Import mechanics

Follow `scripts/load_enrichment_neo4j.py`, which is already the right pattern: it re-reads
every count out of the database after writing, because a `MERGE` can collapse two rows into
one and a `MATCH` can find no endpoint, and neither failure appears offline.

Per import: idempotent, resumable, checksums verified against the manifest, **rows-sent
diffed against rows-landed per dimension per Veda**, and the node and relationship ids
written recorded for rollback.

Rollback is the tested snapshot in `STATUS.md` — loaded into a scratch volume, served on
spare ports and re-counted at 108,779 / 265,295 with all four corpus totals exact.

## Figures that must not move to the product yet

Section F is explicit and it applies to every number in this document. Staged translation
coverage of 18,797 of 20,210 and staged audio of 17,773 of 20,210 are
**STAGED_PROJECTED_COVERAGE**. They may not appear in the frontend, the API, release docs,
the coverage UI or any public report until canonical ingestion and database readback.

The reason is not procedural. Three of these domains found that a figure can be exactly
right and mean something false — the lemma row, the Yajurvedic sort order, the Rigvedic
translation misalignment. A projected figure published before readback is the same class of
claim.

## Known limitations carried into Wave 3

- **Nobody has listened to any recording.** 0 of 150, 0 of 771, 0 of 475, 0 of 25.
- **Nobody has read a cross-Veda pair.** 0 of 6,596 transformation types.
- **There is no human gold anywhere.** 695 rows across three files, 120 `UNANNOTATED` and
  575 model-adjudicated by the family that would be scored. So no precision figure in this
  campaign rests on human judgement, and none claims to.
- **Samavedic morphology is unavailable** on three independent negatives.
- **Samavedic ārcika verse audio is 0 of 1,844**, a verified zero over an assessed
  population. The LOAR deposit does not close it: no item is a Kauthuma ārcika recitation.
