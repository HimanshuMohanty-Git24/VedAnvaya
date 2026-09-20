# Wave 0 — closure and reconciliation

Gap census, corpus audit and source reconnaissance are complete. No canonical graph
mutation occurred; the graph was re-counted after all three agents finished and stands
unchanged at 108,779 nodes / 265,295 relationships.

Registry: `data/gap_registry.json` — 74 gaps, 62 IMPLEMENTATION_GAP, 7 STALE,
5 TRUE_SCOPE_FACT, all `OPEN`, owners 3–16 assigned.

## What the lead re-measured

Every claim below was checked against the live system rather than accepted. Verification
detail is in `agent-1-verification.md` and `agent-2-verification.md`.

| Claim | Verdict |
|---|---|
| AV dedication exists via `HAS_DEVATA_ASCRIPTION`, 4,160 mantras | CONFIRMED — the lead's own baseline was wrong |
| `MENTIONS_LEMMA` reaches 39 distinct lemmas, all theonyms; 9,992 of 10,031 nodes isolated | CONFIRMED |
| AV `SEARCH_DERIVATIVE` deletes base letters — `kr̥dhi` stored as `kdhi` | CONFIRMED |
| ...and causes a live search outage | **DISPROVEN** — the named query returns 24 hits |
| All 1,903 YV translations cite a `:Source` that does not exist | CONFIRMED |
| Gold sets hold zero human annotations across 695 rows | CONFIRMED |
| 475 Samavedic gāna Ogg files on Commons, licence-clean, none fetched | CONFIRMED |
| ...at `PAGE_LEVEL` granularity, and gāna not ārcika | CONFIRMED |
| AV translation gap is 958 in kāṇḍa 20 plus exactly 3 strays | CONFIRMED — 3.9.4, 5.12.11, 10.8.30 |
| YV's 72 concentrate in adhyāya 12 (25) and 23 (13) | CONFIRMED, sums to exactly 72 |
| AV audio gap includes 495 `text_mismatch` | CONFIRMED — and YV 33 |
| `sacred-texts.com` returns 403 | CONFIRMED, including through its own www redirect |

## How the gaps actually decompose

Wave 0's most useful output is not the gap count. It is that several gaps are a different
shape than their size suggested.

**The AV translation gap is one acquisition, not 961 problems.** 958 of 961 are kāṇḍa 20;
both incumbent AV sources omit it for the same Whitney-related reason. One source closes
99.7% of it. The three strays are individually addressable.

**The YV translation gap may not be a gap.** The 72 concentrate in adhyāya 12 (25) and 23
(13) — 23 being the aśvamedha dialogue Griffith suppressed. These are plausibly Griffith's
own cross-references rather than missing text. Two local snapshots settle it. **Do not
source before checking.**

**~43% of the AV audio gap is probably ours.** 495 of 1,159 are recorded `text_mismatch`,
not "not found" — the signature of a numbering offset. A mapping fix, not an acquisition.
The same pattern covers 33 of the YV gap.

**The Samaveda audio gap changed character rather than closing.** Material exists and is
licence-clean, but it is page-level gāna performance. Closing the gap requires verse
boundary verification *and* a separate gāna Work identity. It is no longer
source-blocked; it is not close to closed.

**SV morphology is genuinely unavailable.** Absent from DCS (271 corpora),
UD_Sanskrit-Vedic (57 texts) and VedaWeb (7 texts) — three independent negatives. This is
a candidate for `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE` on evidence, not on giving up early.

## The Samaveda translation decision, resolved against the brief

The only complete public Samaveda translation is Griffith's, and it is **Rāṇāyanīya** on
Griffith's own written testimony ("I have followed Benfey's text"), against our Kauthuma
Ārcika — with three compounding offsets: cross-recension, structural (6 Books against 9
prapāṭhakas) and arithmetic (1,875 against our 1,844).

Section 1 forbids reusing another recension's translation "merely because Sanskrit looks
similar". Section 8 requires 20,210 of 20,210. Those appear to conflict for the Samaveda.
They do not, because section 3 already orders the priorities:

1. Published translation matching the exact recension — **does not exist for Kauthuma.**
2. Alternate published translation matching the exact *text* — Griffith qualifies **per
   verse, only where the Kauthuma verse text actually matches**. The join is the running
   ārcika number, reconciled verse by verse. "Looks similar" is forbidden; *verified
   identical text* is explicitly permitted.
3. Public scholarly edition or scan.
4. Model-assisted literal rendering, clearly typed, never attributed to a translator.

So the Samaveda is worked per verse, not per corpus: each verse lands at whichever tier its
own evidence supports, and the tier is recorded on the row. No blanket decision is taken,
and no verse inherits a neighbour's provenance. This needs no owner ruling — the brief
already specifies it.

## Recension traps Wave 1 must not walk into

Named here because each one looks correct and is not:

- **VedaWeb's only annotated Atharvaveda is Paippalāda.** `avs` carries no annotation layer.
- **`IISHAShuklaYajurVeda`, 55 clips, 37.51 h** — that runtime is the fingerprint of the
  Veda Prasar Samiti **Kāṇva** master, not Mādhyandina.
- **en.wikisource's `Yajurveda` title redirects to Keith's Taittirīya.**
- **Griffith, Stevenson, Benfey and Sāmaśramī are all Rāṇāyanīya** for the Samaveda.
- **Wayne Howard's notation decipherment is of the Jaiminīya**, and `jaiminiya-arseya`
  appears beside the Kauthuma Ārṣeya in search results.
- **`Samved.xlsx` is a verified trap.** Its header promises 1,875 verses; the file holds
  890 rows, 985 of the 1,875 numbers absent across 89 disjoint runs, 70% of rows with
  verse text spilled into attribution columns, and private-use-area font-hack codepoints
  instead of Unicode accents.

## Blockers to name rather than work around

1. **`sacred-texts.com` returns 403 from here.** Re-probed by the lead: 403 direct, and
   403 after following the www redirect. It supplied the 1,903 YV translations from
   snapshots taken 2026-09-07, and the AV kāṇḍa-20 plan depends on it. A reachability
   re-probe is Wave 1's first step; if it stays down, the kāṇḍa-20 acquisition needs an
   independent host.
2. **IGNCA's 40 `SYMS_CHAP_*.mp3` remain 404**, re-verified 17 months on. YV Mādhyandina
   audio would have to be commissioned. This is a genuine external unavailability.

## The prerequisite Wave 1 must satisfy before it writes anything

The graph cannot distinguish *assessed and empty* from *never assessed* for any dimension
except audio, because run provenance is written onto produced artifacts and never onto the
mantra examined. Section 32 requires 100% assessed coverage on optional dimensions, so
that number is currently unreportable.

Therefore every Wave 1 artifact must emit its **assessed set** — the population it
examined — alongside its positives. This is why `manifest.json` requires
`candidates_considered` to balance against accepted, rejected and unresolved. A domain
that returns only its positives cannot close section 32 and will not be imported.
