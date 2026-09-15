# Translation completion — Agent 3, Wave 1

Gap at start: **2,927** verses with no translation, verified against the live graph, not taken
from a list. Gap after this pass: **1,413** on importable rows, **673** of which are rejected
with a per-row reason and 740 of which are staged at `PROBABLE` for verification.

Artifact: `data/staging/translation/`. Validator: **PASS**, all 15 checks at 100% coverage,
2,254 canonical keys resolved against the live store with `veda` agreeing on every one.

```text
.venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/translation --graph
  translation (agent 3): 2254 row(s), 5 source(s)
  740 row(s) at PROBABLE/UNVERIFIED confidence -- staged, not importable
  PASS. Every check evaluated every eligible row and found no defect.
```

No canonical mutation occurred. Every query this agent ran was `MATCH`/`RETURN`, through a
runner that refuses write-shaped Cypher outright.

## The numbers

| Veda | gap | importable now | staged `PROBABLE` | rejected, with reason | residual |
|---|--:|--:|--:|--:|--:|
| RV Sakala | 50 | 13 | 4 | 33 | 37 |
| YV Madhyandina | 72 | **50** | 1 | 21 | 22 |
| SV Kauthuma Arcika | 1,844 | 507 | 735 | 602 | 1,337 |
| AV Saunaka | 961 | **944** | 0 | 17 | 17 |
| **total** | **2,927** | **1,514** | **740** | **673** | **1,413** |

`candidates_considered = 2,927 = accepted 2,254 + rejected 673 + unresolved 0`. The assessed
set is emitted in `manifest.json.assessed_population`, so the import can tell *assessed and
found nothing* from *never assessed* (section 32).

---

## 1. The Yajurveda 72 were mostly a pipeline defect, and the evidence is on disk

**Verdict: 39 of 72 are ours, 21 are a structural divergence, 12 are Griffith's own omission.
Nothing was sourced for the Yajurveda. Nothing needed to be.**

The reconnaissance guessed the 72 were Griffith's cross-references. They are not. They decompose
by *defect*, and the decomposition is exact:

| Stage defect | count | what it actually is |
|---|--:|---|
| `LABEL_NOT_PRINTED` | 39 | **the translation is in the snapshot.** The source's own OCR corrupted or dropped the printed verse number, the adapter correctly refused to guess, and the refusal was recorded as a *source gap* |
| `NUMBERING_SPINE_DIVERGENCE` | 21 | Griffith's adhyaya 12 prints 118 verses against our 117 |
| `PRINTED_OMISSION` | 12 | VS 23.20-31, absent from the print |

### The 39

Each one is a digit confusion, visible the moment the label sequence is laid out. Re-parsing the
pinned 2026-09-07 snapshot of all forty book pages:

```text
adhyaya  6:  ... 22 23 24 23 26 ...        the second "23" is 25
adhyaya  8:  ... 25 26 17 28 ...           "17" is 27
adhyaya 12:  ... 42 43 14 45 ...           "14" is 44        ... 72 73 71 75 ...  "71" is 74
adhyaya 16:  ... 32 33 31 35 ...           "31" is 34
adhyaya 20:  ... 83 84 S5 85 87 ...        three units for slots 84, 85, 86
adhyaya 23:  ... 56 57 68 59 ...           "68" is 58
adhyaya 26:  ... 21 22 28 24 ...           "28" is 23
adhyaya 33:  ... 86 87 38 89 ...           "38" is 88
```

They are recovered by a rule that **refuses when the answer is not forced**: inside each interval
between two bindings the shipped pipeline already made, the unlabelled units are assigned to the
free canonical slots in print order — and only when the two counts are equal.

39 recovered. Two intervals refused (adhyaya 12 and adhyaya 23, below). **Zero regressions**: all
1,889 existing `EXACT` bindings are reproduced byte-identically, and every key the shipped
pipeline bound appears in the new mapping.

That regression control earned its keep. A first attempt maximised a globally consistent anchor
chain by dynamic programming, "recovered" 60 — and silently re-bound 53 verses of adhyaya 12 by
one place, because a global optimiser will happily absorb the 118-against-117 mismatch by
shifting everything before it. The guard caught it. Without the guard it would have read as a
better result.

### The 21 in adhyaya 12

Griffith prints 118 numbered verses where the Madhyandina spine has 117, so exactly one of his
units splits one of ours. The offset was located **per verse**, by comparing his English against
his own Rigveda rendering of the parallel this graph already asserts:

- **12.106 through 12.116**: eleven consecutive verses, each independently agreeing that printed
  label = canonical mantra + 1, at 0.909–1.000 token Dice. Accepted at `EXACT`, each row citing
  its own control.
- **12.117**: the last unit against the last mantra — forced by the boundary, but with no content
  control of its own. Accepted at `PROBABLE`. It does not inherit its neighbour's evidence.
- **12.97 through 12.105**: rejected. Ten printed units for nine slots, and none of the nine has
  a Rigveda parallel to locate the split with. **The English is on disk and is deliberately
  withheld**, because binding it is a one-in-ten guess whose failure mode is silent. Detail and
  three routes to close it: `proofs/yv_adhyaya_12_spine.md`.

### The 12 in adhyaya 23

Not merely absent — **printed as an omission**. Griffith's unit 19 ends:

> Thee, lord of treasures, we invoke. My precious wealth! . . . . . . . . . . . . . . . . . . . .

and the next printed label is 32. That row of dots is the print declining to render the
asvamedha dialogue. Six avenues were checked for the text elsewhere, including the archive.org
scan of the same 1899 edition (same omission, none of the dialogue's catchwords anywhere in
1.04 MB of its OCR) and Keith's Taittiriya (a different samhita — using it would be the exact
cross-recension substitution section 1 forbids). `proofs/yv_adhyaya_23_omission.md`.

One formatting note, checked rather than assumed: the 51 Yajurveda rows keep the source's line
breaks, because 1,855 of the 1,903 incumbent Yajurveda translations already in the graph contain
them. The Atharvaveda, Samaveda and Rigveda rows are whitespace-normalised, matching *their*
incumbent layers. The inconsistency is between the existing layers, not introduced here.

### One judgement call the lead may want to reverse

31 of the 39 recovered rows have **no independent content control** — those verses have no
Rigveda parallel in this graph, so the address rests on the forced interpolation plus the
1,889-row regression control. They are typed `EXACT` because the mapping genuinely is forced
and single-solution, and they carry
`payload.address_forced_without_content_control: true` so they can be filtered out in one
predicate. The other 8 are confirmed against Griffith's own Rigveda English. If the lead wants
only content-confirmed rows, the YV recovery is 19, not 50.

---

## 2. sacred-texts.com: still 403, and now the cause is visible

Re-probed before any acquisition. Four URLs, research UA and full desktop browser UA, direct and
through the `www` redirect: **403 every time**. The body is not an error page, it is a Cloudflare
`Just a moment...` interstitial pointing at `challenges.cloudflare.com`.

So the host is answering, with a **bot challenge**. That is a CAPTCHA by another name, it is out
of bounds, and no attempt was made to clear it. The route is closed by policy, not by luck, and
it should not be retried on the assumption that it is transient.

**Routed around via the Internet Archive Wayback Machine** — a public archive, no challenge,
serving the pre-JavaScript captures of the same pages with their per-verse anchors intact:

| Need | Capture | Result |
|---|---|---|
| Griffith AV kanda 20 | `20230325113203`, 143 hymn pages + index | 144/144 HTTP 200 |
| Griffith AV kandas 3/5/10 | same | 3/3 HTTP 200 |
| Griffith Samaveda, whole work | `20231227014835`, `/hin/sv.htm` | HTTP 200, 284,759 bytes |
| Griffith Rigveda, 16 hymns | `2023` captures | 16/16 HTTP 200 |
| Griffith White Yajurveda | not fetched | the 2026-09-07 snapshot is already local |

Wayback URLs carry an explicit immutable capture timestamp, so the timestamped URL plus the
per-page sha256 in `proofs/source_pages.json` is replayable provenance. Full probe record:
`proofs/sacred_texts_reachability.md`.

One path trap: Griffith's *Hymns of the Samaveda* is **not** under `/hin/sv/` — that 404s and
reads as "the archive does not have it". It is one page at `/hin/sv.htm`.

---

## 3. The Atharvaveda: 944 of 961, from one acquisition

**923** verses come straight from Griffith's *Hymns of the Atharvaveda*, kanda 20 — an
attributed, public-domain, **Saunaka** translation of the kanda itself. No Rigveda substitution
was needed for any of them. The three strays (AVS 3.9.4, 5.12.11, 10.8.30) came from the same
work and the same capture, and are **not** forgotten: they are in `rows.jsonl`, at `EXACT`.

Recension is verified rather than assumed. Griffith's preface (read from the archive.org OCR of
vol. I, `in.ernet.dli.2015.274134`) describes his text as "divided into twenty kandas, Books or
Sections, containing some seven hundred and sixty hymns and about six thousand verses", and
cites *Paippalada* readings as a **different** recension's variants rather than as his base.
Structurally: kanda 20 has **143 hymns in both** his print and our spine, and his per-hymn verse
counts agree exactly on 127 of the 143.

### Two traps inside kanda 20

**The HTML anchor names are wrong, and they are wrong in a way that balances.** `av20120.htm` is
headed `HYMN CXX` and carries anchors that read `20.121.01` and `20.118.02`. An anchor-led parse
therefore invents a verse in hymn 118, invents one in hymn 121, and **loses hymn 120 entirely** —
while the totals still look plausible. Addressing is by the page's own hymn number plus the
printed verse label; the anchors are only a cross-check, and their 3 disagreements are recorded.

**A tiling heuristic that was written, fired, and deleted.** Griffith prints some Kuntapa units
as two canonical verses (`3` in the margin, `4.` inline at the head of the text). A rule that
inferred such spans "whenever the implied ranges tile the hymn exactly" fired on eight hymns and
was **wrong on all eight**: hymn 47 prints verses 1, 2, 3, 10-21, and the arithmetic happens to
balance if you let the unit labelled 3 swallow verses 3-9. Hymn 133 prints one verse and would
have had it copied onto six. Only an *explicitly printed* range is treated as a range now — 68
rows, all typed `VERIFIED_SEGMENT` with `RANGE_ALIGNMENT` and their printed span recorded.

### The 38 kanda-20 verses Griffith's print does not carry

21 of them are closed by the cross-corpus route the brief permits, and **only** under the
condition it sets: the verse's canonical Sanskrit is **surface-identical** (similarity exactly
1.0, accent-stripped and script-folded, comparing this graph's own two text versions) to the
Rigveda verse the graph already asserts a relation to. Those rows are `VERIFIED_SEGMENT`, tier 2,
and their `mapping_method` says in words that this is a Rigveda translation reused across
corpora, citing **both** keys. Near-identical was refused: the 17 rejected rows each record their
nearest parallel and its measured similarity, and the highest of them is below 1.0.

---

## 4. The Samaveda, worked verse by verse

**Tier 1 does not exist.** Nine avenues, all recorded in `proofs/sv_residual.md`. Griffith,
Benfey, Stevenson and Samasrami are all **Ranayaniya** — confirmed today from Griffith's own
preface, verbatim: *"I have followed Benfey's text"*, in a paragraph that names Benfey's and
Samasrami's editions as of the same recension as Stevenson's Ranayaniya.

### Tier distribution, per verse, never per corpus

| tier | rows | confidence | basis |
|---|--:|---|---|
| 2 | **334** | `EXACT` | Kauthuma Sanskrit surface-identical to its Rigveda parallel **and** the Griffith Samaveda unit identified for that verse by content |
| 2 | **173** | `VERIFIED_SEGMENT` | Sanskrit surface-identical to its Rigveda parallel, but no Griffith Samaveda unit pinned — so Griffith's **Rigveda** translation is used, citing both keys |
| 3 | **735** | `PROBABLE` | the Griffith Samaveda unit *is* identified for that verse by content, but the Kauthuma reading is only near-identical, so the reading he translated is not shown to be ours. Staged, **not importable** |
| 4 | 0 | — | not exercised; the named residual |
| — | **602** | rejected | no per-verse evidence at any tier |

507 importable. 1,337 residual.

### The verification method for tier 2, and why it is not a positional join

A positional join was not used, and measurement says it could not have been: the map from our
running order to Griffith's drifts monotonically from offset **0** at the head to **-81** at the
tail. Instead each Kauthuma verse was matched by **content**:

1. Take the Rigveda verse `y` this graph already says our verse `k` reuses or parallels.
2. Take Griffith's own canonical Rigveda translation of `y` — 10,502 attributed rows already in
   the store.
3. Score that English against **every** one of the 1,778 parsed Griffith Samaveda units. Accept
   the best only if it clears 0.60 token Dice *and* beats the runner-up by 0.08.
4. Keep only the longest increasing subsequence of the resulting pairs, so no accepted match
   goes backwards in either running order.
5. Independently, measure our verse's Sanskrit against `y`'s Sanskrit on one cross-script
   surface (Devanagari transliterated to IAST, accents stripped, transcription folded, using the
   repo's own `vedagraph.normalize` helpers). Tier 2 requires **exactly 1.0**.

The same translator rendering the same verse produces nearly the same English, so a strong
unique match *identifies* the unit. It is per-verse evidence, and it is immune to all three
compounding offsets because it never consults position at all.

It also produced two findings worth keeping. First, **the reconnaissance's structural claim is
wrong in our favour**: Griffith's Part II has **nine** Books, not six, matching the nine
prapathakas of the Kauthuma Uttararcika, and Part I Book/Chapter/Decade maps straight onto
CHANDA prapathaka/dasati at the head (SV CHANDA 1.1.6 = Part I Book I Chapter I Decade I verse 6).
Second, the arithmetic delta is ours: the Kauthuma Samhita is independently given as **1,875**
mantras and this graph holds **1,844**.

### What was refused

All 602 could have been given English by joining Griffith positionally. That is precisely the
move section 1 forbids, and the -81 drift shows it would not even have been self-consistent.
182 of the 602 have no asserted Rigveda parallel at all, so nothing verifies them today. Tier 4
— a typed `MODEL_ASSISTED_LITERAL_TRANSLATION` at `quality_class: MODEL_ASSISTED_DERIVATION`,
attributed to no translator — remains the standing route and is named as the residual. No
model-assisted text was written into this artifact, and no rendering anywhere in it is
attributed to a translator who did not produce it.

---

## 5. The Rigveda 50, and a pre-existing defect the lead should see

17 recovered from Griffith's Rigveda pages (13 `EXACT`, 4 `PROBABLE`). 33 rejected. The
breakdown is the interesting part.

- **RV 1.179.1-6** — the whole hymn was simply missing from the incumbent Wikisource layer.
  Griffith's page has all six. Closed.
- **RV 1.53.1, 1.73.1, 10.61.5-9** — printed and labelled. Closed, 7 verses.
- **RV 5.55.8, 9.7.9, 10.48.7, 10.132.5** — the text is printed but **its verse label is not**,
  merged into the preceding verse. Split only because the merged block's printed-line count is an
  exact multiple of that hymn's modal verse length, then placed by forced interpolation. Because
  this involves splitting text rather than just naming it, all 4 are `PROBABLE`.
- **RV 10.86.16-17** — Griffith's own suppression of the Vrsakapi dialogue. Rejected.
- **RV 8.93.29** — the host's file `rv08093.htm` is headed **`HYMN I. Indra.`** and carries ten
  verses. The host's mandala-8 file numbering is not the canonical hymn number; this is the
  Valakhilya permutation, and it is refused rather than guessed. 1 verse.
- **RV 1.65-1.69 verses 6-10 and 1.70.7-11, 30 verses** — and this one is a **defect in
  already-imported data, not a gap.** Griffith's edition divides each of these hymns into **5
  verses where the canonical Sakala spine has 10** (1.70: 6 against 11). The graph has already
  bound his units 1-5 onto canonical verses 1-5 one-for-one — which, under a 5-against-10
  division, means **canonical 1.65.2 is currently carrying the translation of canonical 1.65.3-4**,
  and so on down the hymn. Six hymns, thirty rows of existing translation, silently offset.
  Repairing it means re-aligning imported rows, which is outside this agent's write surface, so
  it is rejected here and raised: **`RV 1.65-1.70` needs a verse-division reconciliation, and the
  30 "missing" verses are the visible symptom of 30 mis-bound ones.**

---

## 6. QA — random and adversarial, and the checks run over the whole population

Sampled population recorded in `proofs/qa.json`: **160 keys** named explicitly across both
regimes — a stratified random sample per source (12 per source, seeded), plus seven adversarial
strata chosen to break specific failure modes: first-verse-of-hymn, addresses recovered from a
corrupt label, printed multi-verse ranges, cross-corpus Rigveda reuse, the **weakest** accepted
English control, the **lowest** Sanskrit similarity accepted at tier 3, and the adhyaya-12 offset
boundary.

The automated checks are then run over **all 2,254 rows**, not the sample, because a check that
only reads a sample reports the sample's health as the artifact's.

| check | eligible | defects |
|---|--:|--:|
| off-by-one numbering (does a neighbour key match the control better?) | 1,088 | **0** |
| structural / chapter shift (matched Samaveda unit monotonic in both orders) | 1,069 | **0** |
| merged verses, undeclared (same English on keys with *different* Sanskrit) | 2,254 | **3** |
| expected corpus repetition (same English on keys with *identical* Sanskrit) | 2,254 | 0 — 72 informational groups |
| split-verse containment | 2,254 | **1** |
| recension and attribution typing | 2,254 | **0** |
| footnote / page-chrome leakage | 2,254 | **0** |
| OCR contamination | 2,254 | **2** |
| source compositor artifact | 2,254 | 0 — 66 informational rows |
| text too short | 2,254 | **0** |
| rejected rows with a substantive reason | 673 | **0** |

**6 defects over 2,254 rows, in three classes:**

- `merged_verses_undeclared`, 3. Identical English on two keys whose Sanskrit differs — AV
  20.38.4/20.70.7, AV 20.47.9/SV UTTARA 1.1.6.3, AV 20.108.2/SV UTTARA 4.2.13.2. These are
  near-variant verses Griffith rendered the same way, but they are reported as unresolved rather
  than explained away.
- `split_verse_containment`, 1. AV 20.17.10's text is contained in AV 20.94.10's.
- `ocr_contamination`, 2. Two Samaveda rows carry source OCR garble verbatim
  (`All-d6ties`, `Good 4re`). Carried through rather than silently corrected.

Two classes were **reclassified after inspection rather than counted as defects**, and both
reclassifications are recorded with their evidence:

- 75 duplicate-English groups first read as merges. 72 of them are the corpus repeating itself —
  kanda 20 is a mass of Rigveda excerpts and reuses them, the Samaveda reuses the same verses
  again, and every key in those groups has the **same** accent-stripped Sanskrit surface. One
  translator producing one rendering is correct there. The check now separates the two cases, and
  the 3 that survive are the defects above.
- 68 rows were flagged as OCR contamination by a rule that included "ends in a comma". That is
  Griffith's compositor, throughout. Counted separately as `source_compositor_artifact`, 0
  defects, so nobody reads them as truncation.

**Human review: 0.** Every figure here is machine-measured.

## Dead ends, named

- **sacred-texts.com** — 403 behind a Cloudflare challenge, still, on every probe. Not transient.
- **en.wikisource "Hymns of the Atharva-Veda"** — re-verified by `list=allpages`: **21 pages**,
  Book 1 and a Book 2 stub. Not a kanda-20 closer.
- **en.wikisource `Yajurveda`** — redirects to Keith's Taittiriya. Wrong Veda, wrong recension.
- **en.wikisource "The Sama Veda"** — one page, preface only. `data/registry/sources.yaml` still
  lists `WIKISOURCE_GRIFFITH_SV` as `BOUNDED_PILOT_ALLOWED`, promising coverage it lacks.
- **`/hin/sv/` on Wayback** — 404. The work is at `/hin/sv.htm`.
- **`archive.org/download/.../in.ernet.dli.2015.274134_djvu.txt`** — 404. DLI items name their
  derivatives after the scanned title (`2015.274134.The-Hymns_djvu.txt`), not the identifier.
- **`archive.org/download/WhiteYajurVeda/..._djvu.txt`** — HTTP 500; the same bytes came back
  from `/stream/`.
- **`archive.org/wayback/available`** — HTTP 429 from this environment. Direct
  `web.archive.org/web/<timestamp>/` works.
- **Devi Chand's Samaveda**, the commercial *Samaveda Samhita* English reprint, and the edited
  Griffith Yajurvedas (Arya, Pratap) — in copyright or not public.
- **`Samved.xlsx`** — not touched. Wave 0's trap finding stands.

## For the lead

1. **Import order.** AV (944) and YV (50) are clean wins. SV tier 2 is 507. The 740 `PROBABLE`
   rows are the verification queue and should not be imported.
2. **The RV 1.65-1.70 verse-division defect is the highest-value thing in this report** and it
   is not a gap — it is 30 existing translation rows bound one place too early. It needs an owner.
3. **Benfey 1848** (`bub_gb_0C_oEB7TkVgC`) is the single highest-leverage remaining artifact: it
   carries Griffith's own base Sanskrit and would convert the 735 SV `PROBABLE` rows to decidable.
4. **Parallels are the Samaveda's real bottleneck**, not translations. 182 of the 602 unresolved
   verses have no asserted Rigveda parallel; each one added makes a verse decidable with no new
   acquisition at all.
5. **The pipeline defect should be fixed upstream too.** `scripts/fetch_griffith_yajurveda.py`
   and `vedagraph.ingest.adapters.griffith_yajurveda` record 39 recoverable verses as
   `LABEL_NOT_PRINTED` source gaps. The adapter is right to refuse; the gap census is wrong to
   believe it. The forced-interpolation rule used here is small enough to fold into the adapter.
