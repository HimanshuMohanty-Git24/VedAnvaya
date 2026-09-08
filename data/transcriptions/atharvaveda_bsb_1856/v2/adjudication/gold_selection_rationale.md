# AV Gold Line Selection — Rationale Recorded BEFORE Reading
Timestamp: recorded before any crop was rendered or read.
Selected from the frozen 81-line calibration set only (policy FROZEN_BEFORE_CALIBRATION).

Existing gold: c032/l12, c032/l19 — both on ONE leaf (canvas 32), stratum `gold_verified`,
pitch 174 px, early-kanda region. Coverage is therefore single-leaf and single-layout.

Selection signals used are DIFFICULTY signals from the already-published baseline
extractor output (marks_detected, word_spans_count, line_pitch). No gold text, no
reader output, and no external Sanskrit corpus was consulted to choose. Selecting on
HIGH mark count, HIGH span fragmentation and ANOMALOUS pitch selects against easy
lines, not for them.

## 1. c430 / l05  — stratum kanda20_area
Axis: late / Book-20 material.
- Only region of the book that is prose-heavy (kanda 20 is largely Rigvedic reuse
  set in a different measure), so accent placement conventions are most likely to
  differ from canvas 32.
- Already flagged in the frozen set as a deliberately-difficult line
  ("leaf 430 was in v2 calib B1 set").
- Accent-dense: 11 marks detected (6 anudatta + 5 svarita) — equal to the densest
  existing gold line.
- 14 word spans.

## 2. c159 / l02  — stratum middle_kandas
Axis: different line pitch / layout.
- line_pitch = 209 px. Every other leaf in the 81-line set sits at 171-179 px.
  This is the SOLE pitch outlier in the whole calibration set, and the accent bands
  are placed as fractions of pitch (ANUDATTA_BAND, SVARITA_BAND), so this line is
  the only direct test that the band placement is genuinely pitch-relative rather
  than tuned to 174 px.
- Same leaf whose sibling line 17 is the single EXTRACTOR_ERROR in the baseline
  (leaf 159 has 15 lines, not 18) — i.e. a leaf with non-standard line count.
- 16 word spans, 10 marks (6 anudatta + 4 svarita).

## 3. c411 / l09  — stratum kanda19_area
Axis: typography / noise-heavy, plus accent-heavy.
- 17 word spans — the second-highest span count in the entire 81-line set (max 20).
  A high span count means the sirorekha column profile is fragmenting, which is
  exactly the condition that stresses `_filter_artifact_spans` and the
  MAX_TOKEN_SPAN_MISMATCH alignment guard. A single unfiltered fragment shifts
  every subsequent carrier assignment by one word.
- Simultaneously accent-dense: 11 marks (6 anudatta + 5 svarita).
- Kanda 19 region, unrepresented in current gold.

## Coverage expansion vs existing gold
| Axis | existing gold | added |
|---|---|---|
| leaves | 1 (c032) | 3 (c159, c411, c430) |
| strata | gold_verified | middle_kandas, kanda19_area, kanda20_area |
| line pitch | 174 | 209, 175, 174 |
| Book 20 | no | yes (c430) |
| span fragmentation | 14 | up to 17 |
| accent density | 10-11 | 10-11 |

## Rejected candidates and why
- c393/l09 (14 marks, max density) — rejected in favour of c411/l09, which is
  nearly as dense (11) AND carries the span-fragmentation axis (17 vs 8 spans).
- c249/l17 (20 spans, max fragmentation) — rejected because it is middle_kandas
  and c159/l02 already occupies that stratum; keeping three distinct strata was
  ranked higher than the marginal 20-vs-17 span difference.
- All 0-mark lines (c032/l00, c015/l00, c015/l02) — rejected: unaccented lines
  cannot exercise detection, class or binding metrics.

## Commitment
These three line IDs are fixed as of this file. No substitution is permitted after
reading. Thresholds in scripts/run_av_calibration.py are NOT to be touched.
