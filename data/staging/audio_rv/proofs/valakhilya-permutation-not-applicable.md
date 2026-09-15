# The Valakhilya trap, tested rather than assumed

The named hazard for this domain is that a source numbers Mandala 8 with the eleven
Valakhilya hymns moved out of sequence, so a key-for-key mapping attaches the wrong
recitation to 55 hymns. It is the defect a listener notices and a schema does not, and this
project has already shipped it once at VedSearch and corrected it.

The new source needed testing for the same thing, and the test had to be run against
measurement rather than against an expectation, because a sheet built from the expected
answer confirms whichever mapping generated it.

Four independent instruments. The first three are structural; the fourth is acoustic.

## 1. The source states the appendix number itself

`GET /api/locations?textSlug=rv&lvl=2&alias=<coordinate>` returns, per stanza, the alias set
VedaWeb keeps for it. For the eleven hymns in question, read 2026-09-15:

| our key | VedaWeb aliases |
|---|---|
| RV 8.49.1 | `08.049.01`, `8.49.1`, `8,49,1`, **`1018,1`** |
| RV 8.50.1 | `08.050.01`, `8.50.1`, `8,50,1`, **`1019,1`** |
| RV 8.59.7 | `08.059.07`, `8.59.7`, `8,59,7`, **`1028,7`** |

The fourth alias is a running hymn number. For RV 9.98.1 it is `810,1`; the inline running
index of 9.98 is 821, and 821 minus the eleven Valakhilya hymns is 810. So the fourth alias
counts hymns in the 1,017-hymn presentation, with the Valakhilya appended as 1018 to 1028.

VedaWeb therefore says, in its own data and in two numbering conventions at once, that its
`8.49` is appendix hymn 1 of the eleven. The identification is the source's, not ours.

## 2. Per-hymn stanza counts fingerprint the order

Every hymn's stanza count was compared three ways: ours, VedaWeb's, and what the
Griffith-appended order would require at the same label. Counted from VedaWeb's own coverage
report over all 10,552 stanzas, and from the canonical graph.

```
   8.48  ours=15  vedaweb=15  griffith-order-would-be=15
   8.49  ours=10  vedaweb=10  griffith-order-would-be=20
   8.50  ours=10  vedaweb=10  griffith-order-would-be=18
   8.51  ours=10  vedaweb=10  griffith-order-would-be=12
   8.52  ours=10  vedaweb=10  griffith-order-would-be=12
   8.53  ours= 8  vedaweb= 8  griffith-order-would-be=12
   8.54  ours= 8  vedaweb= 8  griffith-order-would-be=12
   8.55  ours= 5  vedaweb= 5  griffith-order-would-be=15
   8.56  ours= 5  vedaweb= 5  griffith-order-would-be=21
   8.57  ours= 4  vedaweb= 4  griffith-order-would-be=19
   8.58  ours= 3  vedaweb= 3  griffith-order-would-be=18
   8.59  ours= 7  vedaweb= 7  griffith-order-would-be=15
   8.60  ours=20  vedaweb=20  griffith-order-would-be=15
```

Over the whole of Mandala 8: VedaWeb agrees with the Aufrecht inline order on **103 of 103**
hymns and with the Griffith appended order on **51 of 103**. The two orders differ on 52
hymns, and VedaWeb falls on the Aufrecht side of every one of them.

This is the same instrument `src/vedagraph/editions.py` used to establish the offset in the
first place ("Verified against per-hymn stanza counts and opening lines"), applied to the new
source and returning the opposite verdict: no permutation applies here.

Corpus-wide, the two label sets are a bijection: 10,552 stanzas and 1,028 hymns on each side,
**0** labels unmatched in either direction, and **0** per-hymn stanza-count disagreements
across all ten mandalas. There is no shift anywhere for a coordinate to absorb.

## 3. Text, scored against the whole Rigveda rather than against the expected answer

For each of the 150 stanzas, the text VedaWeb serves at the audio-bearing location was scored
against **all 10,552** Rigvedic stanzas of this corpus, using this project's own
`vedsearch.skeleton` reduction and its calibrated 0.90 threshold. Not "does it match the one
we expect" but "which of the 10,552 does it match best".

- 150 of 150 returned the row's own canonical key as the single best match.
- Minimum best score 0.9242, median 0.98725.
- 148 of 150 also beat the runner-up by the project's 0.05 margin.
- 2 tie with a letter-identical refrain at another coordinate: RV 2.23.19 with 2.24.16, and
  RV 7.67.10 with 7.69.8. Those are genuine textual duplicates, so text cannot separate them;
  both are declared on their rows, and each twin carries its own separate audio file at its
  own coordinate, so there is no file to confuse.

A 296-stanza seeded random sample (seed 4242) from **outside** the gap was scored the same
way as a control, where a rival recording already exists: 293 of 296 unique-best-correct, the
3 exceptions again being identical refrains (RV 3.30.22 / 3.31.22 / 10.104.11 and
RV 4.16.21 / 4.17.21 / 4.19.11).

## 4. Acoustic: the durations track our stanzas, not the permuted ones

All 80 Valakhilya files were fetched and decoded with `ffprobe`, plus all 20 files of hymn
8.60 as the adversarial control and a seeded 120-file random sample (seed 777) as the
baseline. Pearson correlation of measured file duration against the syllable count of the
text, under three assignments:

| assignment | n | r |
|---|--:|--:|
| as mapped, Aufrecht inline | 80 | **0.871** |
| control: off by one stanza | 69 | 0.655 |
| control: Griffith order, shifted +11 hymns | 80 | **0.088** |

For scale, the same correlation over the 120-file random sample is 0.924 and over all 287
fetched files 0.908. The as-mapped figure sits in that family; the permuted assignment is
indistinguishable from noise.

Head to head on the registry's own named stanza, RV 8.49.1: file `08.049.01.ogg` runs 9.13 s
against our 35 syllables, while `08.060.01.ogg` — the file a Griffith-order naming would have
put at 8.49.1 — runs 9.52 s against our 34. Neither is conclusive alone, which is why the
correlation over 80 files is the measurement and this row is only an illustration.

## What this does and does not establish

It establishes that the file the source attaches to a stanza is the file the row points at;
that the source's coordinate system is ours, hymn by hymn and stanza by stanza across the
whole Rigveda; that no edition permutation applies to this source; and that the durations are
inconsistent with the permuted assignment.

It does **not** establish by ear that the audio recites the stanza. Nobody listened. See
`proofs/listening-review-not-performed.md`.
