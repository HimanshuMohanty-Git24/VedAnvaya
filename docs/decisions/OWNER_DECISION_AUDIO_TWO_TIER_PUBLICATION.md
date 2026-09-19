# `OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION` — audible review becomes a badge, not a gate

- **Decision id:** `OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION`
- **Date:** 2026-09-19
- **Provenance:** OWNER-SUPPLIED, relayed verbatim in the VedAnvaya product-restoration
  instruction of 2026-09-19.
- **Status:** In force.
- **Supersedes, in one clause only:** `OWNER_DECISION_E_AUDIO_GATE` —
  `docs/reports/data-completeness/OWNER_DECISIONS.md` §8 ("The listening queue stays
  honest") and §14 ("The audible queue stays mandatory and blocks only audio"), reaffirmed
  at §32, §40 and §43.
- **Does not supersede:** `OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE` (§43), which remains
  exactly as narrow as it states.

## The instruction, as given

> I don't care about Q audio. I want the thing to be done.

Interpreted, and recorded as interpreted so that the reading is auditable rather than
implicit:

> Potentially usable audio must NOT be kept invisible merely because it lacks exhaustive
> individual human audible review. Human audible review becomes an additional QA badge, not
> an absolute visibility gate.

## What the superseded decision said, in its own words

§8 of `OWNER_DECISIONS.md`, recorded before any audio had been heard:

> The 1,021-row audible-review queue is real and the gate is not to be weakened. Automated
> text comparison, metadata review, waveform checks and ASR are **none of them** listening
> review. […] No new fragile audio enters the canonical layer as fully verified until the
> required audible review is complete.

§14 turned that into the publication rule this record supersedes:

> The 1,021 rows stay `WITHHELD_PENDING_AUDIBLE_REVIEW`. No automated text or metadata
> check may relabel them.

§8 and §14 are **not deleted, edited or rewritten**. They remain the record of what was
decided on the day it was decided, and they remain the correct account of why 954 staged
rows sat outside the product for four days. This file is the later decision; the register
keeps both.

## The distinction the earlier decision was protecting, and which survives intact

§8's real content was never "withhold". It was **"automated checking is not listening"** —
that a text comparison, however strong, cannot be reported as a human verdict. That
sentence is untouched and is now enforced in code rather than by withholding:
`PublicationTier.RELEASED_VERIFIED` cannot be constructed without
`audible_review_evidence` naming where the hearing is written down, and
`SOURCE_MAPPED_UNREVIEWED` cannot carry such evidence. Both clauses are in
`AudioRecord._check_internal_consistency` and both are held by tests that mutate the guard
away and prove the test then fails.

What changes is only this: an unheard recording is now **visible and labelled** rather than
**invisible and unlabelled**. The earlier rule protected the reader from a false claim by
showing them nothing; this one protects them by showing them the recording and the claim
that actually backs it.

## The new rule

### Two tiers, and nothing between them

| Tier | Means |
|---|---|
| `RELEASED_VERIFIED` | A named person played this recording and confirmed it is the passage it is mapped to. The evidence row is cited on the record. |
| `SOURCE_MAPPED_UNREVIEWED` | Mapped and checked by instrument; heard by nobody. Published on that basis and described on that basis. |

`AudioRecord.publication_tier` defaults to `SOURCE_MAPPED_UNREVIEWED`, so a catalogue line
written before the field existed is never silently promoted. That default is what keeps all
16,834 incumbent records — none of which any listener has ever heard — in the honest tier
without anyone having to remember to put them there.

### Five conditions, all of which must hold before a source-mapped row is published

1. **The media resolves.** Measured on the day of admission by a real HTTP request against
   the publisher, not read back off the staging row's own `availability` field. Where the
   staging row recorded a `sha256`, the fetched bytes are re-hashed against it.
2. **A canonical mapping exists.** The row names a `canonical_key`, that key is a passage in
   this corpus, and its node type admits the claimed `scope_type` under
   `SCOPE_TO_ENTITY_TYPES`.
3. **Text/source alignment passed.** `text_verified` is true on the row. A row whose text
   comparison did not settle — the eight Yajurvedic `UNVERIFIED` residue rows — is refused,
   not downgraded into visibility.
4. **No rejection stands against that recording.** Checked per *(canonical_key, candidate
   URL)* and per *(canonical_key, candidate source)*, never per key alone: the Rigvedic
   `rejected.jsonl` holds a rejection for all 150 accepted keys, because it records five
   *declined rival sources* for each of them. Excluding on the key would have refused the
   entire admissible set.
5. **Provenance is retained.** `mapping_method`, `source_name`, `source_page`,
   `attribution` and the staging set's own measurements travel onto the published record.

### What may never happen

- No unreviewed recording may be described as "human verified", "audibly verified",
  "checked" or "confirmed" on any surface — API, UI, report or caveat.
- No audio may be fabricated where source media is absent. A passage with no recording gets
  no record; `SOURCE_MAPPED_UNREVIEWED` is a weaker claim, never an invented one.
- No automated check may write `RELEASED_VERIFIED`. That tier is reachable only from a
  decision row in `data/manual/audio_review/sample_decisions.jsonl` whose `media_url` is the
  same URL the published record plays.

## What this decision does *not* establish

It does not turn 954 unheard recordings into reviewed ones, and it does not enlarge
`OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE`. That decision accepted 20 hearings in one stratum
(`AV_COORDINATE_REMAPPED`) as sufficient release-level QA of the acquisition pipeline, and
it says in terms that it is "not evidence about the Rigvedic, Yajurvedic or Samavedic
strata". It remains so. The 20 rows it covers are the only rows in the entire catalogue
eligible for `RELEASED_VERIFIED`, and they earn it individually — by their own
canonical_key and their own media URL — not as a population.

It also does not close `GAP-AUDIO-002`, `-003` or `-004`, which are registry entries with
their own closure conditions, nor does it change the 1,021-row review queue: every row in
`data/staging/audio_review_queue.jsonl` still reads `NEEDS_AUDIBLE_REVIEW`, because nobody
has listened to them and a publication policy is not a hearing.

## Mechanism

| What | Where |
|---|---|
| The tier vocabulary and its two refusals | `src/vedagraph/product/audio/models.py` (`PublicationTier`, `AudioRecord._check_internal_consistency`) |
| The one place the reader-facing sentence is written | `src/vedagraph/product/audio/catalog.py` (`tier_note`, `tier_label`) |
| Addressability measurement | `scripts/audio/probe_staged_addressability.py` |
| Admission of staged rows under the five conditions | `scripts/audio/admit_source_mapped_rows.py` |
| Tier counts on the public API | `GET /api/v1/audio/stats` → `by_publication_tier`, `by_veda_and_tier` |
| Tests | `tests/product/test_audio_publication_tiers.py`, `tests/product/test_audio_catalog.py`, `tests/api/test_audio.py` |
