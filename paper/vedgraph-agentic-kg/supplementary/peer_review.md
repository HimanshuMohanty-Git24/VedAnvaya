# Adversarial review record

Two passes are recorded here: a self-review carried out while the manuscript was
being assembled, and a hostile six-perspective pass commissioned against the
finished draft. Findings from both are listed with what was done about them.

Nothing in this file is a claim that the paper is correct. It is a record of what
was attacked and what survived.

---

## Pass 1 — self-review during assembly

Three substantive defects were found by checking the manuscript's own numbers
against the live graph rather than against the repository reports they came from.
All three are the same failure mode: a figure that was true when it was written and
is not true now, or that was imprecise in the source.

### 1.1 A stale figure inherited from a repository report

**Found:** the draft stated that the Sāmaveda carries **8,559** enrichment edges,
taken from a quality-campaign report.

**Checked:** measured live. Outgoing edges from Sāmavedic mantras, excluding
text-version, translation and containment plumbing, is **11,380**.

**Why it mattered:** the figure is load-bearing — it is the population the paper
says no external annotation can reach, so understating it understates the
limitation.

**Action:** corrected to 11,380, with the definition of the population stated in the
sentence, and added to the fact freeze as
`review.samaveda_enrichment_edges` so it cannot drift again silently.

### 1.2 A registry-to-projection drift, found while looking for something else

**Found:** the Sāmavedic `Work` node in the live graph carries a `completeness`
property asserting "ZERO translations are released (0.0%)". The graph serves 173
Sāmavedic translations.

**Checked:** the registry file that is the source of truth was corrected at the
translation import and now states the position precisely — that the 173 are reused
Ṛgvedic renderings on verified-identical Sanskrit, counted in no Sāmavedic
translation figure. The projection was never re-run.

**Why it mattered:** both statements are defensible in their own terms, and a reader
comparing them would conclude one is a lie. The real finding is that prose-valued
properties are not covered by the invariants that cover typed ones.

**Action:** neither figure is quoted as current. The drift is reported in the paper
as a threat to validity (§9.3) and as future work (§12), and the registry's precise
formulation is the one the paper follows.

### 1.3 An arithmetic term wrong in the repository, and repeated in the draft

**Found:** the draft said "all-pairs over 20,210 mantras is 204 million **ordered**
pairs", quoting a source comment.

**Checked:** $\binom{20210}{2} = 204{,}211{,}945$. 204 million is the *unordered*
count; ordered is 408 million.

**Action:** corrected in the paper, with a footnote naming the discrepancy in the
source rather than silently fixing it.

### 1.4 Two rankings, resolved rather than believed

The project's worst benchmark failure was a sentence whose every figure was real and
correctly cited, and whose comparative words asserted a ranking the cited rows did
not contain. The manuscript makes two empirical ranking claims, so both were
resolved against the live graph before publication:

| Claim | Result | Runner-up |
|---|---|---|
| Sāmaveda has the highest undirected parallel coverage | **holds** — 1,677/1,844 = 90.9 % | Yajurveda 34.8 % |
| Indra is the most frequently dedicated deity (figure selection criterion) | **holds** — 2,869 | Agni 1,988 |

Both are pinned in `fact_freeze.rankings`, and the runner-up is now stated in the
text so a reader can check the claim rather than accept it.

### 1.5 Two determinism hazards in the paper's own tooling

Found by reading the generators rather than by a failing run:

- The subgraph generator derived diagram node identifiers from Python's built-in
  `hash`, which is salted per process, so the generated figure source differed
  between runs. Replaced with positional counters.
- A thousands-separator substitution was applied to a whole formatted string
  rather than to the number inside it, which rewrote a TikZ coordinate.

Neither would have changed a reported figure; both would have made a
"reproducible" figure irreproducible. Recorded in Appendix H.

### 1.6 Four floats defined but never cited

Caught by a cross-check of `\label` against `\cref` rather than by reading.
Fixed; the check is `check_floats` in the build notes.

---

## Pass 2 — commissioned hostile review

A six-perspective adversarial pass was run against the finished draft:
knowledge-graph, NLP/LLM, digital-humanities, Sanskrit/textual-scholarship,
reproducibility, and statistics/methodology. The reviewer was instructed to be
hostile, to try to prevent publication, and to check the paper's claims against the
live graph with its own queries rather than reasoning about them. It read all
sections and appendices, inspected the generator scripts, ran about forty read-only
queries, and ran the repository's own invariant and scorecard scripts.

Its verdict was **major revision**, and it was right. Every finding below was
re-verified independently before being acted on; a few were not sustained and are
recorded as such.

### 2.1 SUSTAINED, and the most serious: the integrity claim was false

The draft said twenty live invariants and eleven scorecard gates "all pass at the
frozen commit". The reviewer ran `scripts/check_live_invariants.py`. We re-ran it:

```
FAIL  edges_without_grade_basis                165,788
FAIL  edges_without_attribution_precision       19,598
warn  assertions_without_predicate_edge          2,193
2 failing, 1 warning, 20 checked
```

The eleven scorecard gates do all read zero; the twenty invariants do not. The
draft had taken "all gates green" from the project's release certification, which
recorded that state truthfully at an earlier census, and had not run the suite.

This is the paper's own thesis committed against the paper: a report was trusted
where a measurement was one command away, in the sentence that certified the graph.
It is now reported in §8.1 as a failure, with the provenance of the mistake, rather
than corrected silently.

### 2.2 SUSTAINED: the untyped edges are graded

4,390 edges carry no knowledge layer. The draft said so. It did not say that **all
4,390 carry `TIER_B`** — the tier meaning "a reproducible rule derived it". An edge
of unknown origin was being presented as reproducibly derived. Verified and now
disclosed, together with two further departures from the documented
tier-from-layer bijection (2,469 deterministic edges at `TIER_D`, 36 source-explicit
at `TIER_B`).

### 2.3 SUSTAINED: 89 % of the model layer is not wired

2,193 of the 2,459 model-extracted assertions carry no `ASSERTION_PREDICATE` edge;
all 2,193 are `MODEL_EXTRACTION`. The repository's own invariant warns about this
and the draft did not mention it. It bears on the headline: wired, the
model-extracted edge count would be 890 + 2,193 and the graph-wide share about
0.6 % rather than 0.17 %. Now stated in §8.2.

### 2.4 SUSTAINED: the headline ratio is a population choice

0.17 % is the smallest of several defensible figures. §8.2 now gives four, measured
rather than argued: 0.17 % of all edges; 0.35 % once the 255,147 plumbing edges are
removed; **7.0 %** over the semantic assertion layer, which is the population where
a model is the proposing mechanism; and higher again if one counts edges owed to a
model proposal rather than only those carrying the layer. The abstract now carries
the 7.0 % figure beside the 0.17 %.

*Note:* the reviewer computed the non-plumbing population as 217,144; our own
measurement is 255,758. We report ours, since it is in the freeze and re-derivable.

### 2.5 SUSTAINED: the freeze records a dirty tree and the title page did not

`git_tree_clean` is *false*. The delta is the paper's own untracked directory, and
`git status --porcelain` reported only that — but a measurement from a dirty tree
is a measurement from a dirty tree, and the title page claimed a commit without
qualification. Now stated on the title page and in Appendix H.

### 2.6 SUSTAINED: the availability statement was false about its own artefacts

At `6bf220c` the entire `paper/` directory is untracked, so the reproduction recipe
cannot be run from the commit the paper cites. Corrected in the availability
statement.

### 2.7 SUSTAINED: the self-correction citation was misapplied

The cited result is about *intrinsic* self-correction without external feedback.
The regime here gives the attacking agent a different instruction and database
access. The citation is now presented as motivation, with the explicit statement
that no cited result predicts the regime will work.

### 2.8 SUSTAINED: the accent enumeration does not cover the flagship case

Appendix B enumerated the tone-mark ranges the stripping function declares. We
extracted every mark from all 1,136 accented Sāmavedic witnesses: they are in
Devanagari Extended (U+A8E1–U+A8F3), and **zero** are in the enumerated
U+0951–U+0954. The 25,542 total is exactly right; the specification was not.
Corrected.

### 2.9 SUSTAINED: a philological term asserted too confidently

The draft called the Sāmavedic three-verse unit a *daśati*, a word meaning a set of
ten. The graph's addressing does use that coordinate, but the modal unit holds
three verses (281 of 458). The text now reports the measured size and declines to
name it.

### 2.10 SUSTAINED as limitations, now in Threats

Thresholds selected on the corpus they are evaluated on, with no held-out set; the
LSH recall claim ("every pair at 0.44 or better") which the standard banding curve
puts nearer 0.94 than 1; and the conflict of commitment arising from a single
decider with a stated devotional relationship to the material. All three are now in
§9.3 rather than absent or buried.

### 2.11 SUSTAINED but not fully fixed

- **`audit_numbers.py` is weak.** It skips every non-integer, passes every integer
  ≤ 100, and whitelists ~250 more. It cannot detect two correct figures swapped
  between sentences. We have moved several whitelisted values into the freeze as
  real measurements, which shrinks the whitelist, but the criticism stands: the
  audit is a drift detector, not a correctness check, and should be described that
  way.
- **Bloomfield's *Vedic Concordance* is still not used as a baseline**, and
  *Rig-Veda Repetitions* is still not cited. The paper names the gap; it does not
  close it.
- **No external text-reuse tool was run as a comparator.**
- **`fig_indra.py` has unbroken ties in its `ORDER BY` clauses** and an asymmetric
  legacy-spelling fold on the L1 side. Not fixed in this revision; recorded here.
- **CIDOC-CRM / FRBR are not cited** although the Work/TextVersion modelling is in
  their territory.

### 2.12 NOT SUSTAINED

- The reviewer's non-plumbing denominator (217,144) did not reproduce; ours is
  255,758.
- The claim that the scorecard gates fail: they do not. All eleven read zero, and
  re-running the scorecard regenerated its committed report byte-identically, which
  is a small positive reproducibility result.

---

## What this record is for

The paper argues that an agent auditing its own output finds less than a
differently-instructed one. Pass 1 was the former and found three figure-level
defects. Pass 2 was the latter and found a false integrity claim, an undisclosed
grade on untyped edges, an unreported wiring defect in the very layer the headline
measures, and a denominator that flattered the result.

That is the paper's own thesis, tested on the paper, with the same outcome.
