# VedGraph: Agentic Construction of an Evidence-Typed Knowledge Graph for the Vedic Saṃhitās

**Author** — Himanshu Mohanty (independent researcher)
**Status** — PREPRINT. Not submitted to any venue.
**Fact freeze** — commit `6bf220c`, branch `main`, clean tree, 20 September 2026.
**Graph measured** — 165,737 nodes / 510,905 relationships / 20,210 canonical mantras.
**Extent** — 47 pages: main body 1–35, references 36, appendices A–H 38–47.
9 figures, 9 tables, 28 verified references.

This directory holds the manuscript and everything needed to re-derive its numbers,
tables and figures. It is a read-only consumer of the VedaGraph repository: nothing
here writes to the graph, the corpus, the registries, the API or the frontend. Every
Cypher statement issued by the scripts in `figures-src/` is `MATCH`/`RETURN`.

---

## What the paper argues

LLM agents were used continuously across the seventeen days and 249 commits that
built VedGraph, and yet **0.17 % of the graph's relationships are model-extracted**
(890 of 510,905), against 21.39 % source-explicit and 77.22 % deterministically
derived. The paper explains the mechanism that produced that ratio — a promotion gate
encoded as data rather than as a review convention — and argues that the durable
contribution of agents in scholarly knowledge-graph construction is the refutations
they can be made to perform, not the claims they generate.

---

## Build

The manuscript is XeLaTeX. It uses only free fonts shipped with TeX Live
(Libertinus), and Sanskrit is set in IAST transliteration throughout, so no Indic
font is required.

```bash
tectonic -X compile main.tex          # produces main.pdf
```

Any XeLaTeX toolchain works; `latexmk -xelatex main.tex` is equivalent. The
bibliography is `natbib` + BibTeX with `plainnat` (author–year).

Tectonic was used for the shipped PDF because it is a single self-contained binary
that fetches the packages it needs, which makes the build reproducible on a machine
with no TeX installation.

---

## Regenerating the numbers

Everything numeric flows from one file, `supplementary/fact_freeze.json`. Nothing in
the prose, the tables or the data figures is typed by hand.

```bash
# 1. Re-measure. Requires the loaded Neo4j store and the repo's .env.
python figures-src/fact_freeze.py        # -> supplementary/fact_freeze.json
python figures-src/graph_census.py       # -> supplementary/census_*.csv

# 2. Re-derive the tables, the data figures and the supplementary CSVs.
python figures-src/make_tables.py          # -> tables/*.tex
python figures-src/make_supplementary.py   # -> supplementary/*.csv
python figures-src/fig_corpus_and_epistemic.py
python figures-src/fig_crossveda.py
python figures-src/fig_samaveda.py

# 3. Re-derive the live-queried figure.
python figures-src/fig_indra.py            # -> figures/fig_indra_generated.tex

# 4. Audit.
python figures-src/audit_numbers.py        # every integer claim vs the freeze
python figures-src/audit_claims.py         # every superlative and absolute
```

Steps 1 and 3 need the graph; step 2 needs only the freeze. If the freeze changes,
re-run step 2 and rebuild: a table and the sentence citing it cannot diverge unless
the freeze itself is stale.

**Dependencies.** Steps 1 and 3 use the project's own virtualenv (`neo4j`,
`python-dotenv`, `pyyaml` — all already project dependencies). Step 2's plotting
scripts additionally need `matplotlib` and `numpy`, which are *not* project
dependencies and should be installed into a separate environment so the product's
environment is untouched:

```bash
python -m venv .venv-paper
.venv-paper/bin/pip install matplotlib numpy
```

---

## Layout

```
main.tex                     the manuscript; \input's everything below
references.bib               bibliography (verified; see below)
sections/                    00-frontmatter … 14-backmatter
appendices/                  A–H
figures/                     compiled figure PDFs + fig_indra_generated.tex
  product/                   the two product screenshots
figures-src/                 every figure and table generator
  vizstyle.py                shared palette and matplotlib style
  fact_freeze.py             THE measurement script
  graph_census.py            label/relationship census -> CSV
  make_tables.py             fact freeze -> tables/*.tex
  fig_*.py / fig_*.tex       one file per figure
  make_supplementary.py      fact freeze -> supplementary/*.csv
  audit_numbers.py           numerical-consistency audit
  audit_claims.py            superlative / absolute-claim audit
tables/                      generated (*.tex) and hand-authored tables
supplementary/               fact_freeze.json, census and evidence CSVs,
                             peer_review.md
CLAIM_EVIDENCE_LEDGER.md     internal audit: every project-specific claim -> its evidence
```

Two tables are hand-authored rather than generated, because they carry judgement
rather than measurement: `tables/failures.tex` (the failure ledger) and
`tables/responsibility.tex` (who did what). Both are cross-checked against the
artefacts named in Appendix F.

---

## Figures

| Figure | Source | Kind |
|---|---|---|
| Corpus, scale and epistemic layers | `fig_corpus_and_epistemic.py` | data, from freeze |
| Agentic construction pipeline | `fig_pipeline.tex` | TikZ schematic |
| Epistemic pipeline and dispositions | `fig_epistemic.tex` | TikZ schematic |
| Core graph ontology | `fig_ontology.tex` | TikZ schematic |
| Propose → attack → adjudicate | `fig_adversarial.tex` | TikZ schematic |
| Cross-Veda reuse matrices | `fig_crossveda.py` | data, from freeze |
| Indra's neighbourhood by layer | `fig_indra.py` | data, queried live |
| Sāmavedic notation before/after Gate C | `fig_samaveda.py` | data, from freeze |
| Product surfaces | `figures/product/*.png` | archived screenshots |

Schematic figures are TikZ so they stay vector and live in version control as text.
Data figures are matplotlib → PDF. No figure is drawn by hand from remembered
numbers.

The two product screenshots come from the archived capture set of 2026-09-19, taken
from the running local product against the same graph census this paper reports
(165,737 / 510,905). Their provenance, viewport and driver are recorded in that
set's own README; nothing in them is mocked or composited.

---

## Colour and accessibility

Figure colours come from a validated palette. The categorical hues are used only for
bars and stacked segments (the *adjacent* pairlist, where four slots pass); they are
never used for a scatter or matrix, where the same four fail the normal-vision floor.
Magnitude uses a single-hue sequential ramp; the evidence tiers use an *ordinal*
ramp, since L1→L4 is a strength ordering rather than a set of categories. Three
categorical slots sit below 3:1 against a light surface, so every figure ships
visible direct labels rather than relying on fill alone — which also makes the
figures readable in grayscale.

---

## References

`references.bib` is verified: every entry has a real author list, title, year and
venue, and a DOI or canonical publisher / ACL Anthology / arXiv URL. No entry was
accepted on recall. Primary source editions are cited from the project's own source
registry (`data/registry/sources.yaml`, `source_artifacts.yaml`, `rights.yaml`)
rather than from secondary description.

---

## Audits run before release

| Audit | How | Result |
|---|---|---|
| Build | `tectonic -X compile main.tex` | 0 errors, 0 undefined references, 0 undefined citations, 0 overfull boxes |
| Numerical consistency | `audit_numbers.py` | PASS — every integer claim resolves to the freeze, a documented parameter, a year or a small count. It is a **drift detector, not a correctness check**: it skips non-integers and cannot catch two correct figures swapped between sentences. |
| Claim audit | `audit_claims.py` | 345 trigger sentences read; the 2 empirical rankings resolved against the live graph and pinned in `fact_freeze.rankings` |
| Visual QA | every page rendered and inspected | no layout defects |
| Adversarial peer review | six hostile perspectives, with its own live queries | **MAJOR REVISION** — 11 findings sustained, including a false integrity claim the draft had taken from the project certification instead of measuring. All acted on. `supplementary/peer_review.md` |

The claim audit exists because of the project's own worst benchmark failure: an
answer whose figures were all real and correctly cited, and whose comparative words
asserted a ranking the cited rows did not contain. A numeric check cannot see that.

---

## Scope of this directory

Per the brief under which it was produced, this work did not modify the product.
No frontend, backend, graph, corpus, registry or API file was changed. The only
files added outside this directory are none.
