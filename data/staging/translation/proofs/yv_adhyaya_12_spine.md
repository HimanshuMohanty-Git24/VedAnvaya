# VS 12.97-117: Griffith prints 118 verses where the spine has 117

Twenty-one of the Yajurveda's 72 missing translations sat in adhyaya 12 from mantra 97 to 117.
Eleven are now accepted with per-verse verification, one is staged unimported, and **nine are
rejected** — because the text exists and the address does not.

## 1. What the shipped pipeline saw, and why it refused

`scripts/fetch_griffith_yajurveda.py` records `NUMBERING_SPINE_DIVERGENCE` at 97 and carries
22 units unbound. Re-parsing the pinned snapshot confirms the count exactly:

```text
adhyaya 12: canonical mantras 117, printed units 117, printed labels ... 96 97 98 ... 117 118
```

Griffith's adhyaya 12 carries **118 printed verse numbers against 117 canonical mantras**, so
somewhere in the adhyaya one of his units is a split of one of ours (or one is an extra). The
pipeline located the disagreement at 97 and declined to bind anything from there on. That was
the right call and it is preserved here: nothing before 97 is touched.

## 2. Locating the offset per verse, not per adhyaya

For each of mantras 97-117 the graph was asked for a Rigveda parallel with a canonical Griffith
Rigveda translation, and that English was compared against every one of the 22 printed units.
Thirteen mantras had such a control. The result:

| canonical mantra | best-matching printed label | token Dice | control |
|---|---|---|---|
| 12.101 | 97 | 1.000 | RV 10.97.23 |
| 12.102 | 103 | 0.620 | RV 10.121.9 |
| 12.106 | 107 | 1.000 | RV 10.140.1 |
| 12.107 | 108 | 1.000 | RV 10.140.2 |
| 12.108 | 109 | 0.949 | RV 10.140.3 |
| 12.109 | 110 | 1.000 | RV 10.140.4 |
| 12.110 | 111 | 0.949 | RV 10.140.5 |
| 12.111 | 112 | 0.985 | RV 10.140.6 |
| 12.112 | 113 | 1.000 | RV 9.31.4 |
| 12.113 | 114 | 0.920 | RV 1.91.18 |
| 12.114 | 115 | 0.909 | RV 1.91.17 |
| 12.115 | 116 | 1.000 | RV 8.11.7 |
| 12.116 | 117 | 0.944 | RV 8.43.18 |
| 12.97-100, 103-105, 117 | — | — | **no Rigveda parallel in this graph, so no control** |

Eleven consecutive verses, 12.106 to 12.116, agree on **printed label = canonical mantra + 1**,
each on its own evidence. Those eleven are accepted at `EXACT`, and every row's
`mapping_method` names its own control rather than the pattern.

Two results are deliberately not used. 12.101 → label 97 would imply an offset of -4 five
verses before a +1 stretch, which no single split can produce; it is a false positive of the
kind a corpus with repeated verses generates, and it is reported rather than hidden. 12.102 →
label 103 scores 0.620, below the 0.90 gate.

## 3. What follows, and what does not

The +1 offset holding from 12.106 means the one extra printed unit lies inside labels **97-106**
— ten units for the nine canonical slots 97-105. None of those nine has a Rigveda parallel to
control against, so which of the ten units is the split cannot be decided from this graph.

- **12.117** is accepted at `PROBABLE`: printed label 118 is the last unit and 117 is the last
  mantra, so the boundary forces it under the verified offset, but there is no content control
  for that verse and it does not inherit its neighbour's.
- **12.97-105** are rejected with `SOURCE_SPINE_DIVERGENCE_UNRESOLVED`. Griffith's English for
  all ten units is present in the pinned snapshot; it is withheld because binding it would be a
  one-in-ten guess applied to nine verses, and a wrong guess would put the wrong English on
  every verse after the split point — silently, which is the whole failure mode this campaign
  exists to avoid.

## 4. How to close the nine

Any one of these settles it, in rising cost:

1. A Rigveda / Atharvaveda / Samaveda parallel for any one of mantras 97-105 added to the graph
   by Wave 1's parallels work: one control inside the window fixes the split.
2. Reading the printed pages 12.97-106 against the Madhyandina Sanskrit for pada count — a
   split unit will be half a mantra.
3. Mahidhara's or Uvata's commentary numbering for VS 12, which is the traditional arbiter of
   where the Madhyandina division falls.
