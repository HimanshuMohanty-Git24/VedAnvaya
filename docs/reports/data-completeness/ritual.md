# Ritual, object and procedure expansion

Agent 13, Wave 2. Artifact: `data/staging/ritual/`. Validator: PASS with
`scripts/validate_staging_artifact.py data/staging/ritual --graph`, 15 checks, every check
at 100% evaluation coverage.

**Nothing was imported.** The canonical graph was re-counted from the live store after the
build and stands unchanged at 108,779 nodes and 265,295 relationships. Every figure below
is *stageable*. The eight modelled rites, three step edges and fourteen wired implements
are still what the product serves.

---

## 1. What the starting position actually was, measured

The brief's estimate was right and the surrounding numbers matter, so all of them were
re-read from the graph rather than inherited. `proofs/samhita-boundary.json` holds the raw
query results.

| | before |
|---|--:|
| `:Ritual` | 8 |
| `:SocialRite` | 5 |
| `:RitualRole` | 11 |
| `:Offering` | 8 |
| `:Object` | 23 |
| `:Substance` / `:Plant` | 15 / 22 |
| `:Action` | 12 |
| `HAS_STEP` | 3 |
| `USES_OBJECT` | 23 |
| `USES_OFFERING` / `INVOLVES_OFFERING` | 4 / 11 |
| `PERFORMED_BY` / `PERFORMED_FOR` | 16 / 9 |
| `USES_SUBSTANCE` / `INVOLVES_SUBSTANCE` | 11 / 3 |
| `INVOKES_DEVATA` | 16 |
| `INVOLVES_RITUAL` | 9 |
| `USED_FOR_RITE` | 529 |
| passages with a `ritual_context` | **0** |

Two registry facts confirmed rather than rediscovered. `GAP-RITUAL-006`: the
`ritual_context` key is absent from `db.propertyKeys()` entirely — confirmed, zero
passages. `GAP-RITUAL-007` is **STALE** — `VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE` exists,
carries 14 supplementary loci and is Saṃhitā-attested. It was measured, not treated as
missing.

All three `HAS_STEP` edges belong to `SOMA-PRESSING` and target `:Action` nodes for the
three daily pressings. The other seven rites have no ordering at all. That existing design
was left alone; the new steps are a separate node kind.

---

## 2. Before and after

| dimension | before | stageable after | new |
|---|--:|--:|--:|
| Rites | 8 `:Ritual` (+5 `:SocialRite`) | **103 attested** | 92 proposed new |
| — of those, named by a core Saṃhitā | — | 45 | — |
| Sub-rite / form-of relations | 0 | 23 | 23 |
| Procedure steps | 3 | **9,273** (3,123 anchored + 6,150 section-expanded) | — |
| Procedures (rite × work) | 1 | 544 | — |
| Ritual roles | 11 | **27** | 16 |
| — classical sixteen officiants | 11 of 16 | **16 of 16** | — |
| Role assignments (`PERFORMED_BY`) | 16 | 179 | — |
| Offerings | 8 | 21 | 13 |
| Implements | 23 (14 wired) | **47** | 24 |
| Materials (substance + plant) | 37 | 32 attested in the apparatus | 32 |
| Actions | 12 | 35 | 26 |
| Rite→item edges | 38 | 685 | — |
| Typed deity→offering edges | 0 (10 generic associations) | 27 | 27 |
| Supplementary works | 0 | **18** | 18 |
| Supplementary loci cited | 0 | 12,393 | — |
| Mantras with a `ritual_context` | 0 | **1,717** of 20,210 | — |

The materials row reads 32 "attested in the apparatus" rather than 69: the candidate space
was a ritual-materials vocabulary measured against the ritual literature, not a merge with
the existing 37 `:Substance`/`:Plant` nodes. The overlap is a lead decision, not a count.

---

## 3. The supplementary corpora, and the boundary they sit behind

This is the part of the brief that was easiest to get wrong, so it is stated mechanically.

**The four core Saṃhitā recensions are untouched.** Verified by re-reading the live store
after the build:

- 4 `:Work` nodes, the same four: `VG:WORK:RV:SAK`, `VG:WORK:SV:KAU`, `VG:WORK:YV:VSM`,
  `VG:WORK:AV:SAU`.
- Per-Veda mantra counts unchanged: RV 10,552, SV 1,844, YV 1,975, AV 5,839 — 20,210.
- Whole-graph totals unchanged at 108,779 / 265,295.
- The supplementary works carry `VG:SUPPWORK:` keys and their loci carry `VG:SUPP:` keys,
  in separate files. They share no namespace with `VG:RV:`, `VG:SV:`, `VG:YV:` or
  `VG:AV:`, and they are not `:Work` nodes.

Every identity is deterministic: `urn:vedagraph:supplementary-work:<slug>`,
`urn:vedagraph:supplementary-passage:<slug>:<citation>` and
`urn:vedagraph:ritual-step:<rite>:<work>:<citation>`, each with a UUIDv5 from
`7c8cde94-2bc0-50e2-8819-568ae65a3ec4` through `src/vedagraph/identity.py`. No random id.

### The eighteen works ingested

Scoped deliberately to the ritual apparatus **of the four recensions we hold**. School
correctness is the whole point of the selection.

| work | type | school | cited lines | loci cited here | attributed translation |
|---|---|---|--:|--:|---|
| Śatapathabrāhmaṇa (Mādhyandina) | BRAHMANA | YV VSM | 17,492 | 645 | — |
| Kātyāyanaśrautasūtra | SRAUTASUTRA | YV VSM | 6,111 | 2,263 | — |
| Pāraskaragṛhyasūtra | GRHYASUTRA | YV VSM | 702 | 308 | Oldenberg, 453 lines |
| Gopathabrāhmaṇa | BRAHMANA | AV ŚAU | 4,391 | 274 | — |
| Vaitānasūtra | SRAUTASUTRA | AV ŚAU | 965 | 391 | Caland (de), 879 |
| Kauśikasūtra | GRHYASUTRA | AV ŚAU | 3,043 | 1,393 | — |
| Pañcaviṃśabrāhmaṇa | BRAHMANA | SV KAU | 3,562 | 291 | Caland, 746 |
| Ṣaḍviṃśabrāhmaṇa | BRAHMANA | SV KAU | 497 | 55 | — |
| Sāmavidhānabrāhmaṇa | BRAHMANA | SV KAU | 289 | 50 | — |
| **Lāṭyāyanaśrautasūtra** | SRAUTASUTRA | SV KAU | 2,634 | 830 | — |
| Gobhilagṛhyasūtra | GRHYASUTRA | SV KAU | 1,088 | 407 | Oldenberg, 1,088 |
| Aitareyabrāhmaṇa | BRAHMANA | RV ŚAK | 2,997 | 556 | — |
| Kauṣītakibrāhmaṇa | BRAHMANA | RV ŚAK | 6,848 | 433 | — |
| Āśvalāyanaśrautasūtra | SRAUTASUTRA | RV ŚAK | 2,836 | 1,222 | — |
| Śāṅkhāyanaśrautasūtra | SRAUTASUTRA | RV ŚAK | 5,238 | 2,264 | Caland (de), 3,425 |
| Āśvalāyanagṛhyasūtra | GRHYASUTRA | RV ŚAK | 763 | 263 | — |
| Śāṅkhāyanagṛhyasūtra | GRHYASUTRA | RV ŚAK | 1,085 | 360 | Oldenberg, 1,077 |
| Kauṣītakagṛhyasūtra | GRHYASUTRA | RV ŚAK | 852 | 388 | — |

61,393 cited ritual-prose lines. **7,668 attributed-translation lines** aligned
line-for-line on the mūla text's own citation; 2,969 of the 12,393 cited loci carry one.

### Thirty-five works refused, with the reason

Three of them are the ones that would have breached the boundary by accident: the
**Taittirīya, Maitrāyaṇī and Kāṭhaka Saṃhitās** are all present in the same repository and
all are Kṛṣṇa-Yajurvedic *Saṃhitās*. Acquiring any of them would have put a fifth Saṃhitā
beside the four. They are recorded as refused, not as unavailable.

Twenty-five more are refused as wrong school, and the dangerous one is named explicitly:
**Drāhyāyaṇaśrautasūtra is Rāṇāyanīya, not Kauthuma.** It is the near-twin of Lāṭyāyana,
it is better covered in DCS's CoNLL-U dump than Lāṭyāyana is, and substituting it would
look like a win. Likewise Jaiminīya brāhmaṇa/ŚS/GS (Jaiminīya Sāmaveda),
Khādiragṛhyasūtra (the Drāhyāyaṇa abridgement of Gobhila), Taittirīyabrāhmaṇa, and the
Baudhāyana / Āpastamba / Bhāradvāja / Hiraṇyakeśi / Vaikhānasa / Mānava / Vārāha /
Āgniveśya / Kāṭhaka apparatus, all Kṛṣṇa-Yajurvedic.

Four more are available and deliberately not taken: the two Āraṇyakas (school-correct but
speculative rather than procedural), the Atharvavedapariśiṣṭa (a late stratum), and
Dārila's and Keśava's commentaries on the Kauśikasūtra — a commentary's claim about a rite
is a claim about a claim, and the closed evidence-type set has no member for that.

### Rights — a finding, not a licence claim

The DCS repository's express **CC BY 4.0** grant lives in `dcs/data/readme.md` and is
scoped to "the data of the DCS and any data in child directories". The Vedic Prose Corpus
sits at `corpus/VPC/`, which is **not** a child of `dcs/data/`, so no express licence covers
the digitisation. What this artifact relies on instead is that each underlying edition is
public domain by age — Weber's Śatapatha, Vedāntavāgīśa's Lāṭyāyana in the Bibliotheca
Indica, Vishva Bandhu's Vaitāna, Caland 1910/1931, Oldenberg SBE 29/30. That is a different
rights basis and it is recorded as one on every source row, for the lead to rule on.

The machine-translation files sitting beside the attributed ones (`-mt` suffix) were
deliberately **not** used. Attributing a model-assisted rendering to a historical
translator is forbidden by the ingestion contract, and an unattributed rendering is not
evidence about a rite.

---

## 4. Procedure: what "source-stated order" was allowed to mean

This is the discipline the brief singled out, so the rule is stated before the number.

**A step is one sūtra, and its position is the position the source prints it at.** Nothing
is interpolated. A rite whose naming sūtras are 5, 9 and 14 gets three steps at those three
citations, and the procedure's `order_completeness` reads `PARTIAL_STATED_POSITIONS` so a
reader can see the run has gaps. Only the eleven Śrauta- and Gṛhyasūtras are used for
procedure; the Brāhmaṇas are narrative and their printed order is not a procedural order.

Two tiers, and only the first is importable:

| tier | what establishes the attribution | steps | evidence layer | confidence |
|---|---|--:|---|---|
| `ANCHORED_SUTRA` | the sūtra names the rite in its own words | **3,123** | `SOURCE_EXPLICIT` | EXACT |
| `SECTION_EXPANDED` | the sūtra stands in a kaṇḍikā where exactly one rite is named | 6,150 | `DETERMINISTIC_DERIVED` | PROBABLE |

Of the 544 procedures (rite × sūtra work):

- **169 are a contiguous printed run** — every sūtra from the first naming to the last, in
  order, with no gap.
- **375 are partial stated positions** — the source names the rite at scattered sūtras and
  those are the only positions asserted.
- **200 of the 3,123 anchored steps carry an explicit sequence word in the sūtra itself**
  (`atha`, `tataḥ`, `paścāt`, `prathamam`, an ordinal…). Those read
  `order_basis: SOURCE_STATED_SEQUENCE_MARKER`. The other 2,923 read
  `SOURCE_PRINTED_SUTRA_SEQUENCE` — the source states the position by printing it in a
  numbered sequence, which is weaker and is labelled so.

So: **169 of 544 procedures have a genuinely contiguous source-stated order; 375 are
partial; and only 200 steps in the whole artifact rest on a sequence word the text
actually uses.** Every step carries its citation.

Largest anchored procedures: yajña 227 steps, dīkṣā 181, darśapūrṇamāsa 180, vaiśvadeva
parvan 172, sthālīpāka 154, atirātra 102.

---

## 5. Evidence-type distribution

The closed set was applied to every assertion. 13,702 typed assertions:

| evidence_source_type | count | share |
|---|--:|--:|
| `SRAUTASUTRA` | 8,476 | 61.9% |
| `GRHYASUTRA` | 3,674 | 26.8% |
| `BRAHMANA` | 1,157 | 8.4% |
| `SAMHITA` | 395 | 2.9% |
| `OTHER_SUPPLEMENTARY_RITUAL_SOURCE` | 0 | — |
| `DERIVED` | 0 | — |

Per assertion class in `proofs/evidence-type-distribution.json`. The distribution is the
point: **97.1% of what this artifact knows about rites is supplementary, not Saṃhitā.** The
Saṃhitā share is exactly the layer that survives the boundary — 45 rite-existence claims,
19 role terms, 41 implements, 25 materials, 21 offerings, 21 actions, and 223 Passage-keyed
`SAMHITA_NAMES_RITE` rows. A Śatapatha line asserting that an oblation goes to Agni is
`BRAHMANA` on its row even where the mantra employed is Yajurvedic; that separation is
mechanical, not editorial.

`OTHER_SUPPLEMENTARY_RITUAL_SOURCE` is empty because the only candidates for it — the
Pariśiṣṭa and the two commentaries — were refused. `DERIVED` is empty because every
derivation still names the source line it derived from.

---

## 6. The mantra bridge, and `ritual_context`

`GAP-RITUAL-006` warns that assigning a ritual context by proximity to ritual vocabulary is
circular, since the ritual vocabulary is the thing the context is meant to explain. This
artifact does not use proximity. The evidence is external: **a named ritual text quotes the
mantra by its pratīka inside an instruction.**

The matcher takes a mantra's opening normalised letters and looks for them at a word
boundary in a ritual line. Three precision controls, each added because a measured sample
showed it was needed:

1. **Word-boundary anchoring.** Without it, mantra openings are found inside compounds.
2. **A two-word minimum span of the mantra.** A one-word match is not a quotation. The
   first sample of 25 contained five plain false positives on single shared words —
   `saṃvatsarasya`, `vaiśvānaram` — matching Brāhmaṇa prose that quotes nothing.
3. **The run must end where a citing word ends.** This one came out of the adversarial
   sample and it was the important one. AVS 4.38.5 opens *sūryasya raśmīn*; eleven ritual
   works quote the standard purification formula *sūryasya raśmibhir iti*. The first twelve
   letters agree, the run stops inside `raśmibhir`, and the `iti` two words later made nine
   works look like they were quoting an Atharvavedic verse they are not quoting. All nine
   are now PROBABLE.

Result over the full assessed population of 20,210 mantras:

| | mantras | rows | links |
|---|--:|--:|--:|
| Reached, EXACT (importable) | **599** | 769 | 870 |
| Reached, PROBABLE only | 1,118 | 2,053 | 2,843 |
| **Reached, total** | **1,717** (8.5%) | 2,822 | 3,713 |
| Unresolved — opening shared with another mantra | 7,851 (38.8%) | — | — |
| No quotation found | 10,642 (52.7%) | — | — |

After the third control, **all 16 of the shortest accepted EXACT rows and all 14 of a
seeded random sample of EXACT rows read as unmistakable pratīka citations**, closed by
`iti`. Examples: ŚBM 3.2.2.19.1 quotes VSM 4.12 for 109 consecutive letters; KātyŚS 2.1.19
quotes VSM 23.33; VaitS 1.4.15 has *yeṣāṃ prayājā iti* for AVS 1.30.4; AB 2.40.4 has *uta no
brahmann aviṣa iti śaṃsati* for RV 3.13.6.

The 7,851 unresolved mantras are the honest core of the negative result. Their first twelve
letters are shared with at least one other mantra, and **6,460 of them have rivals in
another Veda** — the Sāmaveda is largely Rigvedic verse and Atharvavedic kāṇḍa 20 is almost
entirely so. A school prior is available and **was not applied**: a Rigvedic śrautasūtra
quoting a verse shared by the Rigveda and the Sāmaveda is probably quoting the Rigveda, but
that is a prior, and a confident wrong address resolves exactly as cleanly as a right one.
Each unresolved row names its rivals instead. This is the single largest piece of work left.

**The assignment is positive-only, and that is typed in the row.** No mantra anywhere in
this artifact is marked `NON_RITUAL`. A mantra with no citation found may be quoted in a
work not acquired, or quoted by a pratīka shorter than this matcher will accept. So the
material-culture split `GAP-RITUAL-006`'s closure test asks for is **not yet reportable** —
a split needs both sides, and only one side exists.

### Cross-school attribution, measured

27.6% of bridge rows credit a mantra of one recension to a work belonging to another
recension's apparatus (19.9% among EXACT rows). Cross-school citation is real — the
Śatapatha quotes the Rigveda constantly and the Kauśikasūtra quotes it too — so the figure
is not an error rate. It is reported because it is the axis on which a wrong-recension
attribution hides. Full matrix in `proofs/cross-school-census.json`.

---

## 7. The gap registry's own closure tests, run

`proofs/gap-closure-tests.json` runs each test rather than asserting it.

| gap | verdict | the decisive figure |
|---|---|---|
| `GAP-RITUAL-001` rites named but absent | ADVANCED | all four named rites attested and **all four Saṃhitā-attested**: vājapeya 39 loci, rājasūya 12, darśapūrṇamāsa 283, cāturmāsya 20 |
| `GAP-RITUAL-002` procedure unmodelled | ADVANCED | a describing corpus is ingested; 3 → 3,123 anchored steps, every one with a citation |
| `GAP-RITUAL-003` implements | **TEST SATISFIED** | maṇi, dundubhi and audumbara all reached and all wired; yūpa reaches **3 Vedas** with **both VSM 19.17 and VSM 25.29 matched** |
| `GAP-RITUAL-004` roles | **TEST SATISFIED** | **16 of 16** classical officiants attested, none missing; hotṛ carries 27 role assignments across 19 rites; 11 enumerating loci found |
| `GAP-RITUAL-005` deity→offering | ADVANCED | `RECEIVES_OFFERING` proposed, 27 edges, **all 27 `SOURCE_EXPLICIT`** |
| `GAP-RITUAL-006` ritual_context | ADVANCED | key absent confirmed; 1,717 mantras assigned by external citation |
| `GAP-RITUAL-007` aśvamedha | **CONFIRMED STALE** | present, 14 loci, Saṃhitā-attested |

**Not one gap is claimed closed.** `closes_gaps` in the manifest is empty.

The yūpa case deserves its own line because it is the registry's sharpest test and it was a
defect on our side, not a source problem. `GAP-RITUAL-003` records that yūpa "reaches 6 of
11 attested mantras and misses both Yajurvedic witnesses because they are compounds not
registered". Registering `yūpa` as a four-letter word-initial prefix reaches 10 mantras
across RV, YV and AV, including *yūpavraskā*, *yūpavāhāḥ* and *aśvayūpāya* at VSM 25.29 and
*yūpena yūpa āpyate* at VSM 19.17. No acquisition; an alias.

### `RECEIVES_OFFERING` — why this one is `SOURCE_EXPLICIT` and the others are not

The dative case *is* the statement of recipiency. `agnaye puroḍāśam aṣṭākapālaṃ nirvapati`
says the cake goes to Agni; it does not merely mention both. So a dative theonym beside an
offering word is the source speaking, and the dative forms used are lexically unambiguous —
no parser is involved. Agni 55 loci, Indra 54, Āpaḥ 20, Soma 19, the Pitaras 13.

The rite→implement, rite→offering, rite→substance and rite→officiant edges are the opposite
case: they rest on one sūtra naming both things, which is corroboration, not a statement — a
sūtra can name an implement in order to forbid it. All 685 of them are `PROBABLE` and
**none is importable**. Promoting co-occurrence to an asserted relation is precisely the
error `GAP-RITUAL-005` records against benchmark Q4 and Q31, and it is not repeated here.

---

## 8. Corrections to Wave 0's reconnaissance

Measured, not inferred. Each one changes what a later session should expect.

1. **The Kauthuma śrautasūtra is not absent.** Reconnaissance §6 names "the Kauthuma
   śrautasūtra" as *the* hole, on the basis that Lāṭyāyana has two CoNLL-U files in DCS.
   The same repository holds the complete text at `corpus/VPC/Srauta texts/LāṭŚS.txt` —
   **2,634 cited sūtras, prapāṭhakas 1 through 10**, from Vedāntavāgīśa's Bibliotheca
   Indica edition. It is now ingested and it contributes 830 cited loci.

2. **Eggeling in that repository is a 374-line fragment, not the translation.**
   `translations/SB-Eggeling.txt` covers ŚBM 1.3.2 to 3.8.2 and its header records
   `sacred-texts.com` as the digitisation source — the host Wave 0 found returns 403. The
   reconnaissance's expectation of "Eggeling's translation" is sound but it depends on
   **VedaWeb's `sb` text**, which this agent did not reach. The Śatapatha in this artifact
   has no attributed translation at all.

3. **The Pañcaviṃśa is complete, not partial.** Reconnaissance records DCS's CoNLL-U
   Pañcaviṃśa stopping at PB 15,9 of 25 prapāṭhakas. The VPC copy runs PB 1.1.1 to 25.18.6,
   3,562 lines, all 25. Caland's English covers prapāṭhakas 4 and 6–10 only, 750 lines.

4. **The Śatapatha is the one that is partial.** 17,492 lines but only kāṇḍas 3, 4, 7, 8, 9
   and 10 of 14 — the file's own header records the remaining sentence-splitting as work in
   progress. This is the reverse of what the reconnaissance's table implies.

5. **The CoNLL-U file counts have drifted about 40% below the reconnaissance's table,
   consistently.** Measured at commit `8aeed5a1` via the git `trees` API (`recursive=1`,
   24,713 entries, `truncated: false`): Śatapatha 240 files against 361, Gopatha 233
   against 425, Kauśika 141 against 242, Vaitāna 43 against 74, Pañcaviṃśa 169 against 338,
   Kātyāyana 89 against 148. A systematic ratio rather than scatter. The cause is not
   established — a different snapshot, or a double count across a mirrored directory — and
   is named rather than guessed. It does not affect this artifact, which uses the VPC single
   files.

---

## 9. Section 32 and Section I

`candidates_considered` = `accepted + rejected + unresolved` = 3,045 + 47 + 7,851 =
**10,943**, and the validator checks the arithmetic.

That number is a sum, not a population, and one number cannot honestly stand for three
different assessed populations. The manifest therefore carries `populations` separately:
20,210 mantras, 61,393 supplementary lines, 18 works, and named candidate vocabularies of
108 rites, 27 roles, 47 implements, 21 offerings, 35 materials, 36 actions and 30 deity
datives — 304 vocabulary candidates and 53 work candidates, all assessed. The manifest's
`total_candidate_assessments` records 20,572 individual candidate assessments across all
three populations.

Every rejected row carries a reason **and an `outcome`** from a closed set:
`VERIFIED_ZERO` (12), `WRONG_SCHOOL` (25),
`WRONG_RECENSION_AND_WOULD_BREACH_THE_SAMHITA_BOUNDARY` (3), `OUT_OF_SCOPE_*` (5),
`RIGHTS` (1), `INCOMPLETE_FRAGMENT` (1). The count of verified zeros reads the `outcome`
field rather than grepping the prose, because a stale-claim audit in this project twice
certified an absence by grepping for the value it expected instead of enumerating the
field's value space.

Every row carries a `run_provenance` block: `source_snapshot` (the DCS commit and the time
the graph was read), `algorithm_version`, `config_hash`, `code_commit`, `population`,
`processed_count`, `positive_count` with its scope, and `evaluation`.

---

## 10. Two defects this build committed before it measured them

Both are recorded because the fix is less interesting than the failure mode.

**The normaliser destroyed vowel length.** The first `strip_accents` treated U+0304 —
combining macron — as a Vedic accent and stripped it, so `tvā` became `tva` and `hótāram`
became `hotaram`. Every pratīka match would have been unfalsifiable. It was caught by a
census of every combining mark actually present in both corpora rather than an assumed
list, and by the test that now stands in the manifest: **two independent witnesses of RV
1.1.1 — VedaWeb's Aufrecht and GRETIL's Aufrecht, which differ in accent scheme, in
anusvāra, and in the retroflex lateral — normalise to a byte-identical string.** U+0301 is
the udātta over a vowel and the palatal sibilant over `s`, so it is stripped conditionally
on the base character.

**A six-character alias floor produced twenty-three false verified zeros.** The floor was
inherited from the material-culture lexicon audit, where it governed a *substring* pass
over the Sāmaveda. This module matches word-initially, a far narrower opening, and the same
floor silently refused `sruva`, `sphya`, `kapāl`, `musal`, `barhi`, `neṣṭṛ` and twenty more
— and the build then reported their absence as "VERIFIED ZERO over an assessed population".
That is the one substitution the ingestion contract forbids by name. The floor is now five,
a refused alias yields `NOT_ASSESSED_ALIASES_REFUSED` and never a zero, and the count is
now 0. Two of the sixteen classical officiants were in that set; the corrected run reaches
16 of 16.

`proofs/alias-host-forms.json` now prints, for all 345 accepted aliases of 349, the distinct word
forms each actually reached and how often — because alias quality has to be measured per
alias and not per row. Four collisions are named and excluded rather than assumed away:
`grāva` reaching `grāvastut` (the priest, not the stone), `madhu` reaching `madhuparka` and
`madhumattama`, `śyāma` reaching `śyāmāka` millet, and `dakṣiṇā` reaching `dakṣiṇāgni` and
`dakṣiṇāvṛt`, where the word means south and rightward. `darśa` and `aśvina` were dropped
from the registry outright on the same evidence: `aśvina` reaches 28 hits of which all 28
are `aśvinau`, the deity pair.

---

## 11. Known limitations

1. **Nobody read anything.** 0 of 12,393 loci, 0 of 9,273 steps, 0 of 3,045 rows. The
   PROBABLE tiers exist precisely because they need a human read, and none has had one.
2. **Two rite keys are ambiguous by construction and their step counts are contaminated.**
   `VAISVADEVA-PARVAN` (172 anchored steps) shares its name with the Viśve Devāḥ deity
   group, and `VAISVANARA-ISTI` (97 steps) with Agni's commonest epithet. Both are flagged
   in `rites.jsonl`. A reader should assume a substantial share of those 269 steps are
   about the deity, not the rite.
3. **The Kātyāyana yield is low and the cause is ours.** 22 EXACT bridge rows link VSM
   mantras to the śrautasūtra of their own school, against roughly 1,148 `VS.`+`KātyŚS`
   entries recorded in Bloomfield's concordance. Two causes: our VSM text is transliterated
   from a Devanagari Wikisource witness whose orthography differs from the VPC editions,
   and Kātyāyana cites by very short pratīka, often one or two words, which the two-word
   minimum refuses. Neither is a source problem.
4. **The Yajurveda and Sāmaveda have no Latin-script text version in the graph.** All 3,819
   of their mantras were transliterated from Devanagari for this build
   (`TRANSLITERATED_FROM_DEVANAGARI` on every form). The RV and AV have native IAST. The
   asymmetry is a likely contributor to (3).
5. **Four dative theonyms the ritual literature uses have no `:Devata` node.** Prajāpati is
   the significant one — no node exists under any key containing `PRAJA`, and he is the
   presiding deity of the Brāhmaṇa sacrificial system. Also Vaiśvānara, Anumati and
   Aryaman. Reported, not minted: the Devatā class is derived from Saṃhitā dedication, and
   a Brāhmaṇa's recipient is not thereby a Saṃhitā dedicatee.
6. **`RECEIVES_OFFERING` does not exist.** Minting it is an ontology change and the lead's.
   Until then the 27 edges cannot land, and `GAP-RITUAL-005`'s closure test cannot pass.
7. **Sub-rite relations are the curator's claim, not a source's.** All 23 are PROBABLE.
   The loci listed are lines naming both rites, which is corroboration; the part-whole
   relation is drawn from the standard description of the śrauta system.
8. **`iti` detection is deliberately conservative and demotes real citations.** It requires
   the matched run to end where a citing word ends. A genuine quotation whose run breaks on
   a sandhi difference one or two words before the `iti` lands in PROBABLE. Some unknown
   share of the 2,053 PROBABLE rows are correct.
9. **The Śatapatha has no attributed translation here**, and Vaitāna's and Śāṅkhāyana's are
   German. English exists only for Pañcaviṃśa (partial), Gobhila, Śāṅkhāyana GS and
   Pāraskara (partial).
10. **The 108-rite candidate space is named, not exhaustive.** `GAP-RITUAL-001` remains open
    for the reason the registry gives: the denominator is a curation question. 103 attested
    is a count against a list this agent wrote.

---

## 12. Dead ends

- **`sacred-texts.com` was not attempted.** Wave 0 and Wave 1 both re-probed it at 403. The
  only thing this agent needed from it was a full Eggeling, and it turned out the DCS copy
  is a fragment *digitised from* that host. The Wayback route was not tried because
  VedaWeb's `sb` text is the better path and neither was needed for the rest.
- **The DCS `contents` API was not used**, per the brief. The git `trees` API at
  `recursive=1` returned all 24,713 entries with `truncated: false`.
- **`agnicayana` is zero** across all 61,393 lines. The attested form is `agnicit`; the
  later compound is not in this corpus. Same pattern for `antyeṣṭi` (zero — the attested
  forms are `pitṛmedha` and `śmaśāna`), `agnyādhāna` (zero — `agnyādheya`),
  `nirūḍhapaśubandha` (zero — `paśubandha`) and `śrāvaṇī` (zero — `śrāvaṇa`). Five rite
  names are genuinely absent under every form tried and are recorded as verified zeros:
  sarpabali, nakṣatrakalpa, maṇibandhana (the compound; the act is present as *maṇiṃ
  badhnāti*), ṛtupeya and indradhvaja.
- **`maṇibandhana` as a compound does not exist**, which matters because it was the obvious
  way to wire the amulet to a rite. The implement layer reaches maṇi through its own
  inflections instead.
- **UD_Sanskrit-Vedic's 14,548 `IsMantra=True` tokens were reached but not used.** The
  reconnaissance is right that they are a gold-annotated bridge, and the VPC's own
  citation-aligned prose turned out to be the shorter path for a first pass. They remain
  the obvious independent check on this artifact's bridge, and running one against the
  other would measure this build's recall rather than only its precision. That check has
  not been done.

---

## 13. For the lead

1. **Rule on the VPC rights basis** before importing anything from it. The CC BY 4.0 grant
   does not reach `corpus/VPC/`; public-domain-by-age does, but that is a judgement.
2. **Decide whether `RECEIVES_OFFERING` gets minted.** Twenty-seven `SOURCE_EXPLICIT` edges
   are waiting on it, and `GAP-RITUAL-005` cannot close without it.
3. **Decide what a `SupplementaryWork` is in the graph.** These are not `:Work` nodes by
   construction. If they become `:Work`, the "four Works" invariant that this artifact just
   verified stops being a useful check.
4. **The 7,851 shared-opening mantras are the largest single piece of remaining work**, and
   a school prior would resolve most of the 6,460 that span Vedas. It is a model decision
   about whether a prior may set an address.
5. **Reconcile the two step models before import.** The existing three `HAS_STEP` edges
   target `:Action` nodes; the 3,123 proposed here target new `:RitualStep` nodes. Both are
   defensible and having both is not.
6. **Split `VAISVADEVA-PARVAN` and `VAISVANARA-ISTI` from their homographs**, or drop their
   269 steps. As they stand they will overstate two procedures.
