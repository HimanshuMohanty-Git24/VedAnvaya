# Rigveda Mantra Parallel Review

Generated 2026-09-04 from `data/knowledge/rigveda_lexical_v1`.
Policy version: `rigveda-mantra-parallel-policy-v1`.

No verses are reproduced here. Pairs are identified by citation, and judged on
metrics that are stored individually rather than fused into one opaque score.

## Candidate generation

A full comparison would be 55,687,476 pairs. Candidates come from MinHash banding
over token bigram shingles, which is linear in the corpus and deterministic.

| setting | value |
|---|---|
| MinHash permutations | 64 |
| bands x rows | 64 x 1 |
| max bucket size | 1200 |
| candidate pairs scored | 148,092 |
| fraction of all pairs scored | 0.27% |
| largest band bucket | 130 |
| oversized buckets skipped | 0 |

### Measured recall

The configuration was chosen by measurement. Every one of the 613,278 pairs of
Mandala 9 was scored by brute force and compared with what the banding proposed:

| tier | brute force | recovered by LSH | recall |
|---|---|---|---|
| would be ACCEPTED by policy | 3 | 3 | 100% |
| kept as CANDIDATE or better | 74 | 74 | 100% |

Zero buckets were skipped in the full-corpus run, so the size cap cost no recall
there either. Brute force took 405 s for one Mandala; the banding scores the whole
corpus in a fraction of that, which is why no O(n^2) pass exists in the pipeline.

## Exact parallels

'Exact' is not one relation. Levels are kept separate and never collapsed.

| representation | pairs |
|---|---|
| ACCENTLESS_EXACT | 252 |
| LEMMA_SEQUENCE_EXACT | 250 |
| NFC_EXACT | 252 |
| SOURCE_EXACT | 252 |
| TOKEN_EXACT | 252 |

Distinct exact pairs: **256**, in **389** groups across all
levels. Largest group: **14** mantras.

`LEMMA_SEQUENCE_EXACT` (250) is *lower* than `TOKEN_EXACT` (252), which looks
backwards for a coarser relation. It is real and worth keeping: the token and lemma
sequences come from the Zurich annotation, whose base text is Lubotsky, while the
source levels come from the canonical GRETIL/Aufrecht text. Two editions disagree on
two pairs. Collapsing the levels would have hidden that.

### Cross-Mandala exact groups (28 of 77)

| group | size | mandalas | members |
|---|---|---|---|
| 978ce410 | 14 | 3, 10 | RV 3.30.22, RV 3.31.22, RV 3.32.17, RV 3.34.11, RV 3.35.11, RV 3.36.11, RV 3.38.10, RV 3.39.9, RV 3.43.8, RV 3.48.5, RV 3.49.5, RV 3.50.5, RV 10.89.18, RV 10.104.11 |
| 12774ae3 | 2 | 1, 2 | RV 1.23.8, RV 2.41.15 |
| 1b34a12f | 2 | 3, 7 | RV 3.4.8, RV 7.2.8 |
| 1d88e869 | 2 | 6, 7 | RV 6.15.12, RV 7.4.9 |
| 2912992d | 2 | 1, 4 | RV 1.147.3, RV 4.4.13 |
| 3e21fafc | 2 | 1, 10 | RV 1.23.23, RV 10.9.9 |
| 41403914 | 2 | 3, 7 | RV 3.4.9, RV 7.2.9 |
| 4591508a | 2 | 3, 7 | RV 3.4.11, RV 7.2.11 |
| 4632db99 | 2 | 1, 9 | RV 1.91.16, RV 9.31.4 |
| 5313a8a9 | 2 | 1, 5 | RV 1.13.9, RV 5.5.8 |
| 5492c56f | 2 | 3, 6 | RV 3.47.5, RV 6.19.11 |
| 5684fa43 | 2 | 3, 4 | RV 3.52.3, RV 4.32.16 |
| 636a6f51 | 2 | 1, 6 | RV 1.174.9, RV 6.20.12 |
| 69fb1753 | 2 | 1, 9 | RV 1.91.3, RV 9.88.8 |
| 6e9ddd81 | 2 | 3, 10 | RV 3.9.9, RV 10.52.6 |
| 73b60804 | 2 | 1, 10 | RV 1.164.31, RV 10.177.3 |
| 89f4bf7f | 2 | 4, 8 | RV 4.32.13, RV 8.65.7 |
| 8cf0da06 | 2 | 1, 10 | RV 1.23.22, RV 10.9.8 |
| 8dffda09 | 2 | 1, 10 | RV 1.23.21, RV 10.9.7 |
| 9a7042bd | 2 | 4, 10 | RV 4.12.6, RV 10.126.8 |
| b98d8421 | 2 | 1, 10 | RV 1.164.50, RV 10.90.16 |
| c5cb155b | 2 | 2, 6 | RV 2.41.13, RV 6.52.7 |
| cb298d64 | 2 | 1, 6 | RV 1.124.12, RV 6.64.6 |
| cd54f14a | 2 | 6, 10 | RV 6.47.12, RV 10.131.6 |
| e0847c9d | 2 | 2, 10 | RV 2.1.2, RV 10.91.10 |

### Largest exact groups

| size | mandalas | members |
|---|---|---|
| 14 | 3, 10 | RV 3.30.22, RV 3.31.22, RV 3.32.17, RV 3.34.11, RV 3.35.11, RV 3.36.11, RV 3.38.10, RV 3.39.9, RV 3.43.8, RV 3.48.5, RV 3.49.5, RV 3.50.5, RV 10.89.18, RV 10.104.11 |
| 8 | 4 | RV 4.16.21, RV 4.17.21, RV 4.19.11, RV 4.20.11, RV 4.21.11, RV 4.22.11, RV 4.23.11, RV 4.24.11 |
| 7 | 2 | RV 2.11.21, RV 2.15.10, RV 2.16.9, RV 2.17.9, RV 2.18.9, RV 2.19.9, RV 2.20.9 |
| 7 | 3 | RV 3.1.23, RV 3.5.11, RV 3.6.11, RV 3.7.11, RV 3.15.7, RV 3.22.5, RV 3.23.5 |
| 4 | 1 | RV 1.165.15, RV 1.166.15, RV 1.167.11, RV 1.168.10 |
| 4 | 5 | RV 5.42.18, RV 5.43.17, RV 5.76.5, RV 5.77.5 |
| 3 | 10 | RV 10.42.10, RV 10.43.10, RV 10.44.10 |
| 3 | 7 | RV 7.28.5, RV 7.29.5, RV 7.30.5 |
| 3 | 10 | RV 10.42.11, RV 10.43.11, RV 10.44.11 |
| 3 | 2 | RV 2.27.17, RV 2.28.11, RV 2.29.7 |

## Near parallels

### Similarity distribution of scored candidates

| ordered token similarity | pairs |
|---|---|
| >=0.95 | 1 |
| >=0.90 | 1 |
| >=0.85 | 36 |
| >=0.80 | 52 |
| >=0.70 | 45 |
| >=0.60 | 148 |
| >=0.50 | 509 |

### Acceptance policy

Thresholds were set after looking at the distribution above and at the sampled
pairs below, not before. A pair must clear **every** condition; no single metric
carries a pair on its own.

| condition | threshold |
|---|---|
| ordered token similarity | >= 0.8 |
| token Jaccard | >= 0.7 |
| normalized edit similarity | >= 0.8 |
| length ratio | >= 0.6 |
| shorter mantra length | >= 4 tokens |
| kept as candidate | ordered similarity >= 0.5 |

Accepted as `PARALLEL_TO`: **69**. Kept as candidates for review: **792**.
Short mantras are excluded from acceptance on purpose: with four tokens or fewer a
high similarity is reachable by accident.

### Accepted near parallels (highest scoring)

| left | right | ordered | token J | lemma J | edit | length |
|---|---|---|---|---|---|---|
| RV 8.13.18 | RV 8.92.21 | 0.952 | 0.909 | 0.909 | 0.924 | 0.909 |
| RV 1.118.3 | RV 3.58.3 | 0.919 | 0.850 | 0.850 | 0.919 | 0.947 |
| RV 8.36.7 | RV 8.37.7 | 0.895 | 0.810 | 0.800 | 0.940 | 1.000 |
| RV 8.36.4 | RV 8.36.5 | 0.894 | 0.800 | 0.800 | 0.918 | 0.958 |
| RV 1.108.9 | RV 1.108.10 | 0.889 | 1.000 | 1.000 | 0.976 | 1.000 |
| RV 8.35.16 | RV 8.35.17 | 0.875 | 0.765 | 0.765 | 0.924 | 1.000 |
| RV 8.35.16 | RV 8.35.18 | 0.875 | 0.765 | 0.765 | 0.933 | 1.000 |
| RV 8.35.17 | RV 8.35.18 | 0.875 | 0.765 | 0.765 | 0.919 | 1.000 |
| RV 9.34.2 | RV 9.65.20 | 0.875 | 0.778 | 0.778 | 0.949 | 1.000 |
| RV 1.23.20 | RV 10.9.6 | 0.870 | 0.833 | 0.909 | 0.857 | 0.769 |
| RV 10.58.2 | RV 10.58.7 | 0.867 | 0.733 | 0.733 | 0.883 | 1.000 |
| RV 10.58.2 | RV 10.58.8 | 0.867 | 0.733 | 0.733 | 0.873 | 1.000 |
| RV 10.58.7 | RV 10.58.8 | 0.867 | 0.733 | 0.733 | 0.901 | 1.000 |
| RV 8.35.8 | RV 8.35.9 | 0.865 | 0.789 | 0.789 | 0.891 | 0.947 |
| RV 5.44.14 | RV 5.44.15 | 0.864 | 0.882 | 0.882 | 0.914 | 1.000 |
| RV 8.35.13 | RV 8.35.14 | 0.857 | 0.750 | 0.750 | 0.895 | 1.000 |
| RV 10.58.1 | RV 10.58.3 | 0.857 | 0.733 | 0.733 | 0.855 | 1.000 |
| RV 10.58.1 | RV 10.58.4 | 0.857 | 0.733 | 0.733 | 0.834 | 1.000 |
| RV 10.58.1 | RV 10.58.5 | 0.857 | 0.733 | 0.733 | 0.883 | 1.000 |
| RV 10.58.1 | RV 10.58.6 | 0.857 | 0.733 | 0.733 | 0.889 | 1.000 |
| RV 10.58.1 | RV 10.58.9 | 0.857 | 0.733 | 0.733 | 0.864 | 1.000 |
| RV 10.58.1 | RV 10.58.11 | 0.857 | 0.733 | 0.733 | 0.870 | 1.000 |
| RV 10.58.3 | RV 10.58.4 | 0.857 | 0.733 | 0.733 | 0.848 | 1.000 |
| RV 10.58.3 | RV 10.58.5 | 0.857 | 0.733 | 0.733 | 0.848 | 1.000 |
| RV 10.58.3 | RV 10.58.6 | 0.857 | 0.733 | 0.733 | 0.841 | 1.000 |

### Rejected and borderline candidates

Pairs just below the bar, kept as candidates rather than promoted.

| left | right | ordered | token J | edit | length | status |
|---|---|---|---|---|---|---|
| RV 10.58.1 | RV 10.58.10 | 0.828 | 0.688 | 0.878 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.3 | RV 10.58.10 | 0.828 | 0.688 | 0.843 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.4 | RV 10.58.10 | 0.828 | 0.688 | 0.822 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.5 | RV 10.58.10 | 0.828 | 0.688 | 0.871 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.6 | RV 10.58.10 | 0.828 | 0.688 | 0.827 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.9 | RV 10.58.10 | 0.828 | 0.688 | 0.840 | 0.933 | CANDIDATE_PARALLEL |
| RV 10.58.10 | RV 10.58.11 | 0.828 | 0.688 | 0.832 | 0.933 | CANDIDATE_PARALLEL |
| RV 8.35.4 | RV 8.35.6 | 0.821 | 0.727 | 0.775 | 0.950 | CANDIDATE_PARALLEL |
| RV 8.36.1 | RV 8.36.3 | 0.809 | 0.679 | 0.842 | 0.958 | CANDIDATE_PARALLEL |
| RV 8.36.1 | RV 8.36.6 | 0.809 | 0.679 | 0.877 | 0.958 | CANDIDATE_PARALLEL |
| RV 8.35.4 | RV 8.35.5 | 0.800 | 0.667 | 0.821 | 1.000 | CANDIDATE_PARALLEL |
| RV 10.58.1 | RV 10.58.12 | 0.800 | 0.688 | 0.850 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.2 | RV 10.58.10 | 0.800 | 0.688 | 0.848 | 1.000 | CANDIDATE_PARALLEL |
| RV 10.58.3 | RV 10.58.12 | 0.800 | 0.688 | 0.876 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.4 | RV 10.58.12 | 0.800 | 0.688 | 0.855 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.5 | RV 10.58.12 | 0.800 | 0.688 | 0.855 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.6 | RV 10.58.12 | 0.800 | 0.688 | 0.861 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.7 | RV 10.58.10 | 0.800 | 0.688 | 0.864 | 1.000 | CANDIDATE_PARALLEL |
| RV 10.58.8 | RV 10.58.10 | 0.800 | 0.688 | 0.854 | 1.000 | CANDIDATE_PARALLEL |
| RV 10.58.9 | RV 10.58.12 | 0.800 | 0.688 | 0.861 | 0.875 | CANDIDATE_PARALLEL |
| RV 10.58.11 | RV 10.58.12 | 0.800 | 0.688 | 0.854 | 0.875 | CANDIDATE_PARALLEL |
| RV 6.27.1 | RV 6.27.2 | 0.792 | 0.882 | 0.874 | 1.000 | CANDIDATE_PARALLEL |
| RV 8.36.1 | RV 8.36.2 | 0.792 | 0.679 | 0.845 | 0.920 | CANDIDATE_PARALLEL |
| RV 8.36.2 | RV 8.36.4 | 0.792 | 0.704 | 0.867 | 0.920 | CANDIDATE_PARALLEL |
| RV 8.36.3 | RV 8.36.5 | 0.792 | 0.679 | 0.901 | 1.000 | CANDIDATE_PARALLEL |

## Pāda-level parallels

Not implemented in v1, and deliberately not designed out. Every parallel record
carries `unit` (`MANTRA` today, `PADA` reserved) plus optional `subject_locator` /
`object_locator` fields, and every token already knows its pāda, so pāda matching
needs new code but no schema change and no re-identification of anything.

