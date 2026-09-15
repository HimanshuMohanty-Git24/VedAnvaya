# Rigveda audio completion — Agent 4, Wave 1

**Status: CLOSED at EXACT, 150 of 150, with one named residual.**

The 150 missing Rigvedic recitations are closed. Every one of them maps to a discrete audio
file the source attaches to that stanza, so no segmentation was needed and no timestamp is
asserted anywhere in the artifact. The residual is not a verse: it is that **nobody listened**,
and `GAP-AUDIO-004`'s closure test asks for a listening check, so that half of the test stays
open. It is recorded as such rather than quietly satisfied by a pile of metadata agreement.

| | |
|---|--:|
| Gap keys | 150 |
| Accepted at `EXACT` | **150** |
| Accepted at `VERIFIED_SEGMENT` | 0 |
| Unresolved | 0 |
| Verses needing a proof of absence | 0 |
| Candidate mappings considered | 900 |
| Candidate mappings declined | 750 |
| Distinct stanzas examined by some instrument | 581 |
| QA defects | 0 |
| Rows reviewed by listening | **0** |

Artifact: `data/staging/audio_rv/`. Validator:
`scripts/validate_staging_artifact.py data/staging/audio_rv --graph` → **PASS**, every check
evaluating every eligible row.

---

## 1. First question: found-and-rejected, or genuinely absent?

The brief asked this before anything else, because the Atharvaveda gap turned out to be ~43%
`text_mismatch` — found, refused on text, and recoverable by a better matcher rather than by
an acquisition.

**That finding does not transfer. The Rigveda has zero `text_mismatch`.**

`data/product/audio_discovery_report.json`, for the Rigveda: `mapped` 10,402,
`source_has_no_audio` 70, `no_source_verse` 80, and no `text_mismatch` key at all.
70 + 80 = 150 exactly. Independently re-derived from the graph and the shipped catalogue:
10,552 RV mantras minus 10,402 catalogued keys = 150, decomposing into exactly two clusters.

| the split | keys | what it is |
|---|--:|---|
| **Genuinely absent — source publishes no recitation** | 70 | the verse is present at VedSearch as text; its own metadata says `audio.sanskrit = false` |
| **Genuinely absent — verse not in the source's edition** | 80 | RV 8.49.1–8.59.7, the eleven Valakhilya hymns |
| Found but rejected on text mismatch | **0** | — |
| Recoverable by a mapping or numbering fix | **0** | — |

So all 150 needed an acquisition. There was no cheap fix hiding here, and the report says so
before claiming anything else.

## 2. The gap registry's recorded root cause for this gap is wrong

`GAP-AUDIO-004` records that the Valakhilya is missing because "the Griffith permutation
needed to map the Valakhilya insertion was never applied", and that its `source_dependency` is
"NONE for the Valakhilya set — the recordings exist at the source under a different
numbering". Both halves are disproven, and the full evidence is in
`data/staging/audio_rv/proofs/gap-audio-004-root-cause-corrected.md`.

- **The permutation is applied.** `vedsearch_coordinates` routes every Rigvedic sukta through
  `vedagraph.editions.griffith_page`; all 16,834 catalogue rows say so in their own
  `mapping_method`; and `audio_mapping_audit.json` shows it working — our 8.60 → source 8.49,
  our 8.103 → source 8.92, five samples text-confirmed. The 55 hymns the registry warns about
  are already mapped correctly.
- **The recordings are not at the source.** VedSearch's Rigveda holds 10,472 verses in ten
  chapters with **92** hymns in Mandala 8 — the 1,017-hymn presentation, which *omits* the
  Valakhilya rather than appending it. 10,552 − 10,472 = 80. A live probe on 2026-09-15 of
  chapter 8 sukta 93 returns `total_shloks "0"`, while sukta 92 returns rows. `griffith_page`
  maps our 8.49 to the source's 8.93, which the source has never carried, so the transform is
  correct about Griffith and has no target at VedSearch.

This was a source dependency all along. Worth amending in the registry, because as written it
sends the next reader looking for a transform that is already there.

## 3. The strongest new lead, measured

**VedaWeb 2.0's Kirchheiner recitation: fill rate 10,552 of 10,552 — 100%.**

Reconnaissance flagged resource `68b177c068287f35c35d7705` as the only audio candidate in the
whole catalogue with a traceable consent chain, and recorded its coverage as explicitly
unmeasured. Measured on 2026-09-15:

- `GET /api/resources/68b177c068287f35c35d7705/coverage` → `covered` 10,552, `total` 10,552,
  one contiguous range `1.1.1` to `10.191.4`, `rangesCovered` true.
- Second independent read: the resource record's own `coverage` field is `[10552, 10552]`.
- **All 150 of the missing stanzas are covered.**

Each stanza carries one discrete Ogg Vorbis file, e.g.
`https://vedaweb.uni-koeln.de/media/recitations/rv/kirchheiner/08.049.01.ogg`, with the
caption `RV 08.049.01`. So the mappings are whole-file and land at `EXACT`; none needed
`VERIFIED_SEGMENT`, and no start/end offset appears anywhere in the artifact.

Provenance, which is what makes this source different from every other audio candidate in the
project: reciter **Pt. D. P. Kinjawadekar**, Pune, **1983**; collected by the Danish
indologist **Guni Hesting Kirchheiner** (d. 2007); held by the **National Library of Denmark**
(`loar.kb.dk/handle/1902/8015`); segmented by **VedaWeb**, University of Cologne. Every one of
those five facts is now on all 150 rows.

### The second reconnaissance question: are its stanza keys Aufrecht-inline?

Yes, and the source says so itself. Full working in
`proofs/valakhilya-permutation-not-applicable.md`; four instruments:

1. **The source's own alias set.** VedaWeb keeps a fourth alias per stanza that is the running
   hymn number in the 1,017-hymn presentation. RV 8.49.1 carries `1018,1` and RV 8.59.7
   carries `1028,7` — VedaWeb stating in its own data that its 8.49 is appendix hymn 1 of the
   eleven. (Cross-check: RV 9.98.1 carries `810,1`; its inline running index is 821, and
   821 − 11 = 810.)
2. **Per-hymn stanza counts.** Mandala 8's counts agree with the Aufrecht inline order on
   **103 of 103** hymns and with the Griffith appended order on **51 of 103**. Hymn 8.049
   carries exactly 10 stanzas where the Griffith order would require 20. Corpus-wide the two
   label sets are a bijection: 10,552 stanzas, 1,028 hymns, **0** unmatched labels in either
   direction, **0** per-hymn stanza-count disagreements.
3. **Text, scored against the whole Rigveda.** Not "does it match what we expect" but "which
   of the 10,552 does it match best". 150 of 150 returned the row's own key as the single best
   match; minimum 0.9242, median 0.98725; 148 of 150 also beat the runner-up by the project's
   0.05 margin.
4. **Acoustic.** Duration against our own syllable counts, over the 80 Valakhilya files:
   r = **0.871** as mapped, **0.655** for an off-by-one-stanza control, **0.088** for the
   Griffith +11-hymn control. Baseline over a 120-file random sample is 0.924.

### Pāṭha type is not claimed

The source does not state it, so `patha_type` is null on every row and nothing in the artifact
asserts saṃhitā-pāṭha. Measured over 287 fetched files the rate is 0.213–0.382 seconds per
syllable (median 0.284), which is continuous recitation and inconsistent with pada-, krama-,
jaṭā- or ghana-pāṭha. That is an inference from a measurement, and an unstated field does not
get filled in from an inference.

## 4. Rights: usable by reference, not by mirroring

The Royal Danish Library's item statement, read 2026-09-15: *"Copyright protected, but you can
use it for non-commercial purposes"*; republishing requires **a written agreement** with the
library; users must credit the author. No SPDX or Creative Commons identifier is given, and
the VedaWeb resource record's `license` and `licenseUrl` are both null.

Therefore, on all 150 rows: `licence` null (the source states none), `local_copy_permitted`
**false**, the library's statement verbatim in `rights_statement`, the collector and holding
institution named, and `playback_mode` `REMOTE_DIRECT` against the source's own host.

**One decision for the lead.** `REMOTE_DIRECT` is a value the product's own `PlaybackMode`
enum already carries, but all 16,834 existing records are `PROXIED_STREAM`. Either mode works
here; **caching does not**, without that written agreement. Flagged rather than decided,
because it touches the player and the player is not this agent's write surface.

## 5. What was declined, and why

`rejected.jsonl` holds 750 rows: each of the 150 keys evaluated against each of the five
declined sources, with a closed `reason_code` and a locator per row. The declined set is where
wrong-verse errors hide, so it is enumerated per key rather than summarised per source.

| source | what it offers | disposition |
|---|---|---|
| **VedaWeb / Kirchheiner–Kinjawadekar 1983** | one Ogg per stanza, 10,552 of 10,552 | **ACCEPTED**, 150 |
| VedSearch (incumbent) | one file per verse, 10,472 rows | 70 flagged no-audio; 80 absent from its edition |
| Royal Danish Library LOAR deposit | the master behind the accepted source | declined as a *direct* route: cassette-side files, no per-stanza boundary |
| `archive.org/details/Rg-veda-shakala-auro1` | **1,028 files, one per hymn, Valakhilya included** | declined on granularity: a whole hymn as one mantra is forbidden; no cue index; no rights statement |
| `archive.org/details/rig-veda_recitation_202009` | 54 tracks of ~44 min, hymn ranges | declined: multi-hymn tracks with self-declared approximate ends; Mandala 8 stops at hymn 92 |
| `archive.org/details/RigvedaChanting` (Veda Prasara Samiti) | 55 tracks of ~44 min, Public Domain Mark 1.0 | declined: no locator below "Part NNN". The only rights-clean candidate and the least mappable |

Also checked and not pursued: **Vedic Heritage / IGNCA**, withdrawn from this product by prior
decision and re-confirmed 404 in Wave 0.

**The near-miss worth naming.** `Rg-veda-shakala-auro1` is the only public *per-hymn* Rigveda
recitation found that carries the Valakhilya, and its 1,028 files reproduce the Śākala
per-mandala hymn counts 191/43/62/58/87/75/104/103/114/191 exactly — an independent structural
witness that the Valakhilya belongs inline. It fails only on granularity, and it fails
completely: no cue sheet, no chapter marks, no timestamps, and the `.afpk` files beside the
audio are Internet Archive fingerprint peaks rather than cue indexes. Recorded as the fallback
if the accepted source goes dark. ASR could have proposed boundaries for it and for the two
monolithic items; by campaign rule an ASR proposal never establishes a mapping, so none was
run.

## 6. An incidental finding: the 70 are a shared lacuna, not a harvesting failure

`rig-veda_recitation_202009` — a different uploader, a different master — labels its own tracks
with where it breaks off:

```
Track  8 - M1_S129 to M1_S145(incomplete)
Track 27 - M6_S53  to M6_S75(incomplete)
Track 30 - M7_S41  to M7_S67 (incomplete)
Track 33 - M8_S4(partial) to M8_S13(incomplete)
Track 43 - M9_S86(partial) to M9_S97(incomplete)
Track 44 - M9_S99  to M10_S5            <- M9_S98 skipped outright
```

Its incomplete hymns are 1.145, 6.75, 7.67, 8.13 and 9.97, and it omits 9.98 entirely. Those
are **66 of the 70** verses VedSearch flags as having no Sanskrit recitation. Two independent
circulating pārāyaṇa recordings break off at the same six places, so the 70 are a lacuna in
the pārāyaṇa material that reaches this product rather than a harvest that went wrong. The
four that do not line up are the isolated singles 1.117.6, 2.23.19, 3.8.5 and 10.56.7.

All 70 are present in the Kirchheiner collection, which is the argument for preferring an
institutional deposit over a circulating copy.

## 7. QA — what was checked, and on what population

Eleven checks, each reporting the population it evaluated. **0 defects, and no check below
100% coverage.** Full detail in `manifest.json` under `qa.detail.checks`.

The accepted population is small enough to audit whole, so it was audited whole rather than
sampled:

| instrument | population |
|---|--:|
| media URL fetched byte-for-byte and decoded by `ffprobe` | 150 of 150 accepted rows |
| row's `checksum` and `duration_seconds` re-derived from the fetched bytes | 150 of 150 |
| coordinate agreement on three surfaces — location alias set, file caption, file name | 150 of 150 |
| text scored against all 10,552 Rigvedic stanzas | 150 of 150 |
| payload constructed through the product's frozen `AudioRecord` (`extra="forbid"`) | 150 of 150 |
| every key resolves to an RV `Mantra` in the live graph | 150 of 150 |
| every key evaluated against every declined source, closed `reason_code` | 750 of 750 |

Adversarial and control populations on top of that:

- **296 out-of-gap stanzas**, seeded random (seed 4242), text-scored the same way where a rival
  recording already exists: 293 unique-best-correct. The 3 exceptions are letter-identical
  refrains (RV 3.30.22 / 3.31.22 / 10.104.11, and RV 4.16.21 / 4.17.21 / 4.19.11) — textual
  duplicates, not mapping errors.
- **120 media files**, seeded random (seed 777), for the duration baseline.
- **All 20 files of hymn 8.60**, the adversarial control for the Valakhilya permutation.
- 287 files fetched in total; **0 fetch failures**.

**Two accepted rows carry a declared caveat.** RV 2.23.19 is letter-identical to RV 2.24.16,
and RV 7.67.10 to RV 7.69.8, so the two pairs tie on text and text alone cannot separate them.
Both are declared in their own `mapping_method` and in `manifest.measurements`. They remain
`EXACT` because the mapping rests on the source's own coordinate and the structural bijection,
and because each twin carries its own separate audio file at its own coordinate — there is no
file to confuse.

### The residual: rows reviewed by listening — 0

Stated plainly, because the alternative is to let section 7 be read as a listening sheet. It
is not one. `proofs/listening-review-not-performed.md` sets out what the structural chain does
establish — that the file the source attaches to a stanza is the file the row points at, and
that the source's coordinate system is ours — and what it cannot: whether the voice recites the
text. Only a listener answers that.

`GAP-AUDIO-004`'s closure test has two clauses. The count clause is satisfied on import. **The
listening clause is OPEN.**

The sheet design is in that proof, and the important part of it is negative: this project has
already been caught by a listening sheet whose decisive row quoted what a *broken* mapping
would have played. So the sheet must give the reviewer **both** candidates — the row's own
stanza and the one the rejected hypothesis would put there, RV 8.49.x beside RV 8.60.x — in
randomised order and unlabelled, with both texts read out of the canonical store rather than
out of the source under test.

Also unheard: no independent check that the reciter is Pt. D. P. Kinjawadekar. That is the
library's and VedaWeb's attribution, carried on the row as theirs. It is the only audio source
in this catalogue that names a reciter at all — but a named reciter is a claim by a named
institution, not a measurement.

## 8. Dead ends, named

- **`griffith_page` at VedSearch for the Valakhilya.** The transform is right and the target
  does not exist. Re-probed live; do not retry.
- **VedSearch for the 70.** The flag is not stale: these are the only 70 rows in the whole
  10,472-row harvest with `audio.sanskrit = false`, and the same verses are missing from an
  independent recording.
- **ASR-driven alignment of the three Internet Archive items.** Not attempted, by rule: ASR
  generates candidates and never establishes a mapping.
- **A licence identifier for the accepted source.** There isn't one. VedaWeb's `license` and
  `licenseUrl` are null and the library gives prose, not SPDX. Do not go looking again; the
  prose is quoted verbatim on every row.
- **Caching the accepted audio.** Blocked on a written agreement with the Royal Danish
  Library. Not a technical blocker and not one to work around.

## 9. Handed on, outside this write surface

- **`GAP-AUDIO-005`, partial credit only.** These 150 rows carry a real `sha256`, a decoded
  duration, a named performer, a named collector, a named holding institution and a verbatim
  rights statement, against the gap's finding that all four are null on every catalogue row.
  That is 150 of 16,984. It does not close the gap, and the other 16,834 rows are untouched.
- **The same deposit holds the other three Vedas.** The LOAR item is 224 cassettes covering
  all four Vedas across six oral traditions, with **named reciters** including M. Ittiravi and
  T. Narayanan Nambudiri for the Samaveda. Wave 0 closed the Samavedic audio gap partly on the
  finding that every candidate has an unnamed reciter; this deposit does not. Whether it
  carries ārcika saṃhitā-pāṭha rather than gāna is **not established here** and is not this
  agent's to establish. Flagged for the lead and for agents 5 and 6, with no claim attached.
- **A rival Rigvedic recitation for the 10,402 already mapped.** The accepted source covers
  all 10,552 stanzas, not only the 150. A second attributed recitation beside the incumbent's
  unattributed one is available for the asking; this artifact deliberately does not propose it,
  because the brief scoped this agent to the gap.
