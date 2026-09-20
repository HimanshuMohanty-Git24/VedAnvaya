# Agent 2's corpus audit — lead verification

Agent 2 returned eleven structural defects and five disagreements with committed reports.
This records which of them the lead re-measured against the live system and what came back.
Not everything was re-measured; what was not is listed at the end as unverified rather than
accepted.

The reason for doing this at all: an earlier session in this project accepted an
evaluator's NOT_READY verdict that rested on a "never projected" claim which one query
disproved. An agent's confident absence, and its confident defect, both need checking.

## Confirmed

**Dedication has a second mechanism — Agent 2 is right and the lead's baseline was wrong.**

```
MATCH (m:Mantra)-[:HAS_DEVATA_ASCRIPTION]->() RETURN m.veda, count(DISTINCT m)
  -> AV 4160
```
The lead's baseline counted only `HAS_DEVATA` and reported the unmodelled dedication
population as 9,658. The true figure is 5,498. `BASELINE.md` finding 1 is corrected and
the original wording is kept visible.

**CORPUS_D01 — the AV `SEARCH_DERIVATIVE` layer deletes base letters, not only accents.**

For `VG:AV:SAU:K01:S002:V002`:

| Role | Text |
|---|---|
| `PRIMARY_TEXT` | `jyā̀ke pári ṇo namā́śmānaṃ tanvàṃ kr̥dhi` |
| `PARALLEL_TEXT` | `jyāke pari ṇo namāśmānaṃ tanvaṃ kṛdhi` |
| `SEARCH_DERIVATIVE` | `jyāke pari ṇo namāśmāna tanva kdhi` |

`kr̥dhi` is stored as `kdhi` and `tanvàṃ` as `tanva`. The normaliser is stripping the base
letter along with its combining mark wherever the mark is a below-dot or below-ring
(U+0323, U+0325) — which in IAST are part of the letter (`ṛ`, `ṃ`), not accents. All 5,839
AV mantras carry such a layer.

## Confirmed, with the stated symptom disproven

Agent 2 reported this as a live product failure: that
`/api/v1/search?q=kr̥dhi&veda=AV` "returns 0 passages though AVS 1.2.2 contains it".

It does not. Measured against the running API:

| Query | AV passage hits |
|---|---|
| `kṛdhi` (precomposed) | 24 |
| `kr̥dhi` (r + U+0325) | 24 |
| `tanvaṃ` | 23 |
| `kdhi` (the corrupted form) | 0 |

Real user queries succeed, because the query is normalised by the same broken rule as the
index, so both sides are mangled identically and still match. The corruption is symmetric,
which is exactly why it survived to production unnoticed.

So the defect is real and worth fixing, but it is not a search outage, and three
consequences are worth separating:

- Snippets drawn from that layer are unreadable.
- Any future consumer reading `SEARCH_DERIVATIVE` as text gets corrupted Sanskrit.
- Precision is silently reduced: `ṃ`-distinctions and vocalic `ṛ` collapse, so the index
  conflates forms the corpus distinguishes.

Had the lead taken the report at face value, this campaign would have opened by announcing
a user-facing search outage that does not exist.

**CORPUS_D02 — confirmed.** All 1,903 Yajurveda translations carry
`source_id='SACRED_TEXTS'`. The `:Source` nodes present are GRETIL, GRIFFITH_WHITE_YAJURVEDA,
VEDAWEB, VEDSEARCH, VHP, WIKISOURCE_GRIFFITH_RV, WIKISOURCE_GRIFFITH_SV, WIKISOURCE_SA and
WIKISOURCE_WHITNEY_AV. There is no `SACRED_TEXTS`, and `GRIFFITH_WHITE_YAJURVEDA` — the
node that should carry these — is referenced by nothing.

This matters beyond tidiness. The lead's baseline reported provenance coverage as present
for 100% of passages by counting the property. Every Yajurveda translation's provenance
chain is in fact dangling, so the 100% was measuring the presence of a string, not the
resolution of a reference. A coverage figure that counts a field rather than resolving it
will report full provenance over a broken graph.

## Accepted but not independently re-measured

Recorded so a later session knows these rest on Agent 2's measurement alone:
CORPUS_D03 (`:Source` has zero relationships), CORPUS_D04 (AV translations attributed to
VEDAWEB but Whitney/Lanman by their own fields), CORPUS_D05 (zero `PADAPATHA`
TextVersions against a `:Work.scope` that claims padapatha is carried), CORPUS_D06 (no YV
`PRIMARY_TEXT` role), CORPUS_D07 (parallels directed, YV has zero outgoing), CORPUS_D08
(`:SourceArtifact` declared, zero nodes), CORPUS_D09, D10, D11, and the assessed-versus-
never-assessed provenance analysis.

CORPUS_D05 and CORPUS_D04 should be re-measured before any product surface is changed on
their basis, because both concern claims the API currently serves.

## The two traps Agent 2 avoided, worth keeping

Both would have produced a confident wrong number, and both are the same shape: counting
codepoints instead of testing meaning.

1. A codepoint-range scan over Vedic Extensions reports 780 Yajurveda texts as accented.
   U+1CEA and U+1CEC are anusvāra marks, not tone marks. The registry's "unaccented" claim
   is correct.
2. U+0301 is both the udātta tone mark and the IAST acute in `ś`. Counting it reports all
   5,839 deliberately-unaccented AV layers as accented.
