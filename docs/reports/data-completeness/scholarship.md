# Scholarly and commentarial disagreement — Wave 2, agent 14

`data/staging/scholarship/` — 114 rows, 112 passages, 17 asserters, 17 works.
`scripts/validate_staging_artifact.py data/staging/scholarship --graph` **PASSES** at 100%
evaluation coverage on all fifteen checks. **No canonical write occurred**; the graph was
re-counted at the start and stands at 108,779 nodes / 265,295 relationships.

## The starting position, re-measured rather than accepted

`GAP-SCHOLARSHIP-001` makes four claims about the graph. All four hold.

| Claim | Measured |
|---|---|
| 6 `:InterpretiveClaim` nodes | CONFIRMED |
| `asserted_by` is the empty string on every one | CONFIRMED — all 6 |
| No scholar or commentator entity exists | CONFIRMED — `CALL db.labels()` returns 48 labels, none of them a person |
| No two claims about the text contradict each other | CONFIRMED — `CONTRADICTS` carries 2 edges, one bidirectional pair |
| `AGREES_WITH` / `QUALIFIES` exist in the ontology | **DISPROVEN** — neither relationship type exists; `CALL db.relationshipTypes()` lists 66 and neither is among them |

Four of the six existing claims are about *this dataset* rather than about the Vedas, and
the one `CONTRADICTS` pair says so itself. `VG:CLAIM:SV-IDENTITY-IS-MELODIC` carries, in
its own `about_basis`: "the pair is a CROSS-CATEGORY methodological disagreement about what
textual overlap implies, not two rival readings of the Vedic text." That sentence is the
most important thing in the existing layer, and it is the reason for the one blocking
prerequisite in §"Before any of this is imported" below.

## What the layer holds

| | rows | CONTRADICTS | AGREES_WITH | QUALIFIES |
|---|--:|--:|--:|--:|
| Atharvaveda Śaunaka | 107 | 87 | 4 | 16 |
| Rigveda Śākala | 7 | 5 | 1 | 1 |
| Yajurveda Mādhyandina | 0 | 0 | 0 | 0 |
| Samaveda Kauthuma | 0 | 0 | 0 | 0 |
| **Total** | **114** | **92** | **5** | **17** |

The Yajurvedic and Samavedic zeros are verified over an assessed population, not unknowns —
see the section on them below.

93 rows are `EXPLICIT`, 21 `HEDGED` — the reporting source states the verdict but hedges it
("probably without authority"). Polarity and confidence are two axes, and collapsing them
would either lose the rejection or overstate it.

**Ten disagreement axes**, all closed vocabulary, all enumerated in
`graph_proposal.json`: `TEXTUAL_READING` (49), `GRAMMATICAL_OR_LEXICAL_ANALYSIS` (47),
`LEXICAL_OR_SEMANTIC_ANALYSIS` (6), `METRICAL_IDENTIFICATION` (5),
`ATTRIBUTION_OF_AUTHORSHIP` (2), `REPORT_OF_A_THIRD_PARTYS_READING` (2),
`REFERENT_IDENTIFICATION` (1), `MORPHOLOGICAL_OR_LEXICAL_ANALYSIS` (1),
`INTERNAL_DIVERGENCE_BETWEEN_TWO_WORKS_OF_ONE_COMMENTATOR` (1), and
`EDITORIAL_TEXT_DECISION` (0 accepted — see the refusals).

**Asserters** (17), each carrying `attribution_status` because one of them is an ascription
the reporting source itself disputes: the Atharvaveda *bhāṣyakāra* ("Sāyaṇa" of the AV,
`ASCRIPTION_DISPUTED_BY_THE_REPORTING_SOURCE`), Sāyaṇa of the Rigveda, the author of the
Bṛhatsarvānukramaṇī (`ANONYMOUS`), Whitney, Lanman, Max Müller, Oldenberg, Roth, Shankar
Pandurang Pandit, Roth-and-Whitney as editors, Wilson, Ludwig, Weber, Grassmann, Ryder, the
manuscript-and-oral authorities for the vulgate (`COLLECTIVE`), and the Bombay edition's
own title-page ascription (`PRINTED_ASCRIPTION`).

**Works** (17), and the distinction that matters: 9 of them were *not read directly*. Every
such row carries `read_directly: false` on its source record and names the witness that
reports it. A graph that cannot say "we read Whitney reporting the commentary, not the
commentary" is a graph that will eventually claim to hold a commentary it has never opened.

## Four disagreements, and what the two positions cannot both be true about

**1. One word, two cases — and the authorship question that hangs on it.**
AV 18.2.46, Whitney–Lanman HOS vol. 7, printed p. lxviii.

> If, by way of comparing the two comments, we take the accusative plural *yamárājñas*, we
> find that at RV. x. 16. 9 Sāyaṇa explains it quite rightly as a possessive compound,
> *yamo rājā yeṣāṁ, tān*; while at AV. xviii. 2. 46 … "Sāyaṇa" makes of the very same form
> a gen. sing, and renders 'by a safe road belonging to king Yama' …

Incompatible about: the case and number of *yamárājñas*. Genitive singular (the road
belongs to Yama) or accusative plural possessive compound (the Fathers have Yama as king).
Different case, different number, different syntactic head — the two cannot both be the
grammar of the line. Three rows come out of this one passage: the grammatical disagreement
at AV 18.2.46, an `AGREES_WITH` at RV 10.16.9 where Lanman endorses Sāyaṇa on the identical
form, and an `ATTRIBUTION_OF_AUTHORSHIP` disagreement — the Bombay edition ascribes the AV
commentary to Sāyaṇa ("comm. = the commentary on AV. (ascribed to Sāyaṇa …)", HOS vol. 7
p. cii) against Lanman's "Such bungling can hardly be the work of a man who knew his
Rig-Veda as the real Sāyaṇa did." That is recorded `HEDGED`, because Lanman calls a
systematic comparison of the two *bhāṣyas* work still to be done, and the volumes' own index
lists it as an open question (HOS vol. 8, p. 1043).

**2. A named translator against the commentary, with the reporting source stating the
conflict.** RV 1.37.1, Max Müller SBE 32, printed p. 63 ff. (the note on verse 1 runs to
p. 66).

> Wilson translates *anarvâ´nam* by *without horses*, though the commentator distinctly
> explains the word by *without an enemy*.

Incompatible about: whether *an-arván* is the privative of *árvat* 'horse' or of *árvan*
'hurting'. Müller sets the two against each other with "though", so the incompatibility is
printed rather than inferred — and he goes on to decide for the commentator. This is the row
that shows why the wording rule matters: had Müller merely printed Wilson's and Benfey's and
Ludwig's renderings side by side, as he does for every verse, there would be no
disagreement to record.

**3. Two renderings, each printed with the Sanskrit it implies.** AV 3.14.4,
HOS vol. 7, printed p. 110.

> Weber renders "like dung" (as if *çákā* = *ćákṛt*); Ludwig, "with the dung" (as if *çákā*
> = *çáknā́*)

Incompatible about: which stem underlies *çákā*. This is the only row in the whole artifact
from that family, and it exists because Whitney prints the implied form for each rendering.
18 further notes where translators differ in English with no implied form stated were
refused — see below.

**4. One author's two commentaries against each other.** AV 18.3.66, HOS vol. 8, p. 867,
in Lanman's ell-brackets.

> Sāyaṇa, commenting on the RV. vs., says *he vena*; but in his comm. on TB. he says *he
> pravargyasvāmin*: an interesting diversity of opinion!

Incompatible about: whom the verse addresses. Two commentaries bearing one author's name
supply two different vocatives for the same verse. This gets its own axis
(`INTERNAL_DIVERGENCE_BETWEEN_TWO_WORKS_OF_ONE_COMMENTATOR`) because it is not a
commentator against a philologist, and flattening it into the same bucket would lose what
makes it interesting.

## Whitney's own evaluative vocabulary decides the relation

The single design decision that makes this artifact possible: the relation is read off the
reporting source's printed words, never from the two positions differing. Whitney writes
"senseless", "wholly without authority", "plainly wrong" — and he writes "doubtless true",
"correctly", "is doubtless the right form". Those are not the same relation. A pipeline that
took every "the comm. explains X, but …" as a contradiction would have converted 5
agreements and 17 qualifications into disagreements, and the artifact would have reported 114
disagreements where there are 92.

Each row carries `relation_basis` naming the verbatim phrase the relation rests on, so a
reader can check the classification against the page rather than trusting it.

The lexicon needed a negation guard. "unacceptable" and "not unacceptable" differ by one
word and by the whole relation, and the first pass labelled AV 2.36.4 a contradiction on the
strength of the substring.

## What was refused, and why — 2,347 candidates

This is the most informative part of the artifact. `candidates_considered` = 2,461 =
accepted 114 + rejected 2,347 + unresolved 0.

| Refused | n | Why |
|---|--:|---|
| Paippalāda manuscript variants | 1,745 | A recension witness is not a scholar. Whitney cites `Ppp.` in 2,603 of 4,933 notes; admitting them would swamp the scholarly layer with text criticism that holds no attributed position. |
| Manuscript variation with no named position | 222 | A collation is evidence, not a claim. Nothing is attributable to a person or a work. |
| The Anukramaṇī's **silence** | 159 | "the Anukr. takes no notice of the deficiency" records the index saying *nothing*. Two sources that do not both assert something cannot be incompatible about it. This is the largest metrical family in the source and none of it is a disagreement. |
| A position + a clause with no verdict | 108 | It cannot be told from the page whether the reporting source contradicts, endorses or qualifies. The relation is not guessed. |
| Reading could not be isolated as a word-form | 22 | "the comm. has nothing better than *hiṅs* to suggest for *ubj*" is a gloss proposal, not a variant reading. |
| **The two printed editions differ** | 19 | Refused wholesale, and this is the biggest real loss. Berlin and Bombay do print different text at these places and Whitney says so, but he says it as "SPP. reads the former and our edition the latter". A first attempt templated these and produced the claim *"The text to print at AVS 4.4.8 is accordingly"* — the regex had captured an adverb. Closing this needs the printed editions, not a better regex. |
| Translators differ in English only | 18 | No underlying reading, derivation or referent stated. Different English for the same Sanskrit is not a disagreement. |
| A second disagreement at the same (passage, work) | 15 | The contract forbids duplicate `(canonical_key, source_id)` pairs. Held back, not discarded. |
| The Anukramaṇī **refuses** a resolution | 9 | Refused wholesale. Whitney records the refusal and calls the contraction "common", but states no incompatible syllable count. An earlier version inferred one and wrote a sentence of the pipeline's own composition as position B — precisely the invention this domain forbids. |
| Verdict clause is the commentary's own content | 3 | "the comm. reads instead *bhrājam*, and absurdly explains it as *bhrājamānām*" — everything after "absurdly" is still the commentary. Attributing it to Whitney would invent a position. |
| Contrast marker inside the first side | 10 | The split fell later than the sentence turns, so the first side swallowed the reporting source's words. |
| Three parties in one span | 4 | Which two the author set against each other is not on the page. |
| Verdict clause continues the same party | 3 | A source at odds with itself is not two sources at odds with each other. |
| Sides too short to separate as clauses | 6 | "comm. has the" states no position. |
| Note could not be anchored to a hymn | 3 | 154 of 4,933 note blocks are unanchored. |
| Anukramaṇī's metre quoted then endorsed | 1 | Agreement does not belong in the disagreement layer. |
| Reporting author's first person on the wrong side | 1 | The split fell inside his own sentence. |

Every figure above is read from `rejected.jsonl`, and the seventeen buckets sum to 2,347
exactly. 26 distinct rejection reasons in all. Every rejected row carries the matched span
and the printed locator, so each refusal is checkable by opening the page.

## Extraction method, and what the model did

**The claims are not LLM output.** 99 rows come from ten deterministic pattern families over
the parsed notes; 15 are hand-adjudicated from the printed page. Every quote is re-verified
as a verbatim substring of the pinned snapshot by `proofs/selfcheck.json` before the artifact
is written: 114 of 114 witness quotes found, 198 of 198 claims that declare themselves
verbatim confirmed, 0 failures. The self-check is not decoration — it caught 17 real defects
on its first run, including one row whose "reading" was the adverb *accordingly* and nine
whose position B was a sentence the pipeline had written.

**The model's only job was to try to disprove rows.** Provider `openrouter`, model
`nvidia/nemotron-3-ultra-550b-a55b:free`. **4 calls**, capped at 4, batched 6 rows per call,
80–177s each, **no retry on any rate-limit or quota error** — this project has paid for that
lesson. The sample is 12 adversarial (the shortest quotes, i.e. least context and likeliest
over-reads) plus 12 random, from the accepted `CONTRADICTS` rows.

Two earlier probes of the provider are recorded too: the first timed out at the configured
60s, the second answered in 96.5s. The configured free model is usable for a bounded batch
and unusable for anything at scale.

### The QA pass dissented, and the dissent is worth reading

**12 of 24 rows carry no verdict at all** — two of the four batches came back as
chain-of-thought prose instead of JSON. Of the 12 it did adjudicate: **5
`REAL_DISAGREEMENT`, 7 `NOT_A_DISAGREEMENT`.** Its reason, verbatim and identical six times:

> Quote reports a variant between commentary and main text, not a scholarly dispute; both
> readings can coexist in different witnesses.

That is a substantive challenge to the largest family in the artifact, so it is adjudicated
in `proofs/qa_dissent_adjudicated.json` rather than buried. Four grounds for keeping those
rows:

1. **The dissent is internally inconsistent.** The same model, in the same run, called AVS
   6.117.2 (*dadhmas* against *dadmas*), AVS 11.2.19 (*martyam* against *matyam*) and AVS
   11.3.37 (*satsyanti* against *çatsyanti*) `REAL_DISAGREEMENT`, while calling AVS 11.8.33
   (*ni* for *vi*) and five others of the identical shape `NOT_A_DISAGREEMENT` with the same
   boilerplate sentence. All six refusals came from one batch. That is an unstable
   classifier, not a reasoned objection.
2. **The brief names "a reading" as a qualifying axis**, alongside a referent, a grammatical
   analysis, an identification and a date.
3. **The commentary's readings are the commentator's, on the reporting source's own
   testimony**: "In books i.-iv. Whitney counts over three hundred peculiarities of the
   commentator's text" (HOS vol. 7, p. lxviii). Whitney reports them as his, not as a
   manuscript's.
4. **The artifact already applies the model's own principle where it holds.** 1,745
   Paippalāda variants and 222 bare manuscript variations were refused for exactly the
   reason the model gives. The line drawn is: *a variant with a named holder is a position;
   a variant without one is evidence.*

**One part of the dissent was fair and did change the artifact.** On AV 9.6.17 the model
said "Whitney reports the Anukramaṇī's view; no second position opposes it." That is a
reasonable reading of the `as if` rows, where Whitney asserts the contrary by implication —
"the Anukr. calls it an ārcī paṅkti, as if it had 30 syllables" — rather than printing a
rival scansion. Those rows now carry `relation_caveat` on `position_b` saying so, and
`METRICAL_IDENTIFICATION` (5 rows) is named here as the weakest evidential shape in the
artifact.

**21 defects were found and fixed during the build**, by the self-check and by reading the
output: 17 on the self-check's first run and 4 more on my own adversarial read of the
non-`CONTRADICTS` rows and the shortest quotes. Each fix is recorded as a rejection reason
citing the passage that exposed it — AVS 4.4.8 for the adverb-as-reading, AVS 1.16.1 for the
commentary's content attributed to Whitney, AVS 6.30.2 for the late split, AVS 3.24.6 for the
three-party span, AVS 2.36.4 for "not unacceptable", AVS 19.13.1 for a position of thirteen
characters.

## Before any of this is imported — one blocking prerequisite

`CONTRADICTS` already exists and carries 2 edges. Reusing the type is right — two
relationship types both meaning "these disagree" is how an attribution axis ends up with
three disagreeing writers — but the existing pair is **not** an attributed scholarly
disagreement. It is this project's own reading against this project's own measurement, and
neither side has an asserter.

So every new edge must carry `disagreement_scope`, and **the two existing edges must be
backfilled to `disagreement_scope: CROSS_CATEGORY_METHODOLOGICAL` before these rows land.**
Without that, the product question "what do scholars disagree about here?" would return the
Samaveda melodic-identity pair as though a scholar held it. That is the exact failure
`GAP-SCHOLARSHIP-001` describes, and importing on top of it would hide the gap rather than
close it.

The full model — four new labels, six new relationship types, the `CONTRADICTS` decision with
its measurement, and the identifier policy — is in `graph_proposal.json`. `VG:SCHOLAR:` and
`VG:SWORK:` are new deterministic prefixes; no existing identifier is proposed for change, and
no `ScholarlyWork` is given a `VG:WORK:` identifier, because that would change what every
per-Veda denominator means.

## The Yajurveda and the Samaveda are verified zeros, and they are not the same zero

`proofs/yv_sv_verified_zero.json`.

**Yajurveda: 0 rows over an assessed population.** All 45 locally pinned sacred-texts pages
of Griffith's *Texts of the White Yajurveda* were searched for every commentator name in the
domain vocabulary. Zero occurrences of Mahīdhara, Uvaṭa, Sāyaṇa, Weber or "commentator" —
because the snapshot is of the translation only and Griffith's footnotes, which do cite
Mahīdhara and Uvaṭa, are not in it. This is an acquisition not attempted in this wave, not an
unavailability. The printed Griffith and Mahīdhara's *Vedadīpa* are both public domain.

**Samaveda: 0 rows, and a recension wall.** All four available Samavedic translations and
commentaries — Griffith, Stevenson 1842, Benfey 1848, Sāmaśramī's Bibliotheca Indica with
Sāyaṇa — are **Rāṇāyanīya**, against our Kauthuma ārcika. A disagreement between two
Rāṇāyanīya witnesses would be attached to a passage of a recension we do not hold. The one
right-recension commentary that *is* reachable is the Kauthuma **Ārṣeya Brāhmaṇa with
Sāyaṇa's commentary**, 14 Sanskrit Wikisource pages under CC BY-SA 4.0. It was not worked
here because it is untranslated Sanskrit: extracting an attributed position from it safely
needs a translation or a Sanskritist, and inventing one is the single thing this domain must
not do.

## Two findings worth carrying forward

**A proofread transcription beats a scan of the same book.** The archive.org full-text layers
for SBE 32 and SBE 46 were fetched and abandoned. The English prose OCRs adequately; the
transliterated Sanskrit does not — *kṛṇavāma* comes out as `Kyvzzdvama`, *pravṛddha* as
`pravrzddha`, *chādayatha* as `#Aadayatha`. Every disagreement in these volumes turns on a
Sanskrit form, and a claim whose Sanskrit cannot be quoted correctly cannot be re-found by
hand. The scan is better evidence and worse data. `proofs/archive_org_ocr_is_unfit_for_sanskrit_quotation.json`.

**The Wayback route works, with two traps.** `sacred-texts.com` is still 403 from this host.
98 of 98 SBE 32 pages and 167 of 167 SBE 46 pages returned 200 through
`https://web.archive.org/web/2023id_/<url>`, and the transcription preserves the printed page
numbers inline as `p. NNN` — which is the locator every row needs. The traps: the `id_` form
answers **302** and must be followed, so `curl` without `-L` reports a zero-byte body that
looks like a dead URL; and archive.org rate-limits, returning 429 on the first probe while
other agents were fetching. It was not retried in a loop. The fetch ran once at 1.2 requests
per second and completed with zero failures.
`proofs/sacred_texts_403_and_the_wayback_route.json`.

## Known limitations

1. **The Atharvaveda carries 94% of the rows.** That is where the source is, not a
   judgement about where the disagreements are.
2. **One commentary dominates.** 93 of 114 rows have the AV *bhāṣya* as position A. The
   layer answers "what does the commentary get wrong here?" far better than "what do
   scholars disagree about?"
3. **One witness reports most of it.** Whitney–Lanman is the reporting source for 108 rows.
   A second independent witness for the same passages would let the reports be cross-checked;
   Bloomfield's SBE 42 is the obvious candidate and 125 of its 217 pages were fetched in this
   wave but not extracted. That is the cheapest next increment.
4. **No `EDITORIAL_TEXT_DECISION` row survived.** The 19 candidates are real disagreements the
   artifact cannot state precisely enough.
5. **`GAP-SCHOLARSHIP-002` is not closed and was not attempted.** No post-Saṃhitā corpus is
   held, and that is a declared scope decision, not a defect.
6. **`GAP-SEMANTICS-004` is only partly unblocked.** Its implementation dependency was a named
   asserter, which now exists; but no stratum map is ingested and none should be until one is
   chosen and attributed.
7. **Zero human annotations.** Consistent with the rest of this project's gold, and the reason
   every row carries a printed page rather than a confidence score. The 15 curated rows were
   adjudicated by reading the page; the 99 templated rows were adjudicated by rule, and the
   rules are in `manifest.json` under `config`.
8. **The RV layer is 7 rows** out of 526 note units across 58 hymns. SBE 32 and SBE 46 are
   rich in disagreement and poor in the *formulaic* disagreement a pattern can catch safely;
   Müller argues in paragraphs. Precision was kept and recall given up.
9. **Rigvedic page locators are the hymn's opening printed page, not the note's exact
   page.** sacred-texts preserves `p. NNN` markers inline, but a note that opens before the
   first marker inside it inherits the page carried in from the translation above. RV
   1.37.1's row says "printed p. 63, note on RV 1.37.1" where the note itself begins on
   p. 65. The locator is re-findable by hand — open p. 63 and read forward to the note on
   verse 1 — but it is not the tight page reference the Atharvavedic rows carry, and it
   should not be quoted as one. The 108 Atharvavedic rows take their page from the running
   head of the page the note is printed on and are exact.
