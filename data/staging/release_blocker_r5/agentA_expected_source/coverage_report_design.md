# How to measure "entities the expectation lists but the registry lacks"

Agent A, R5. Design only. Nothing here was applied and no node was written.

## 1. The rule this design exists to obey

A coverage report must never divide by a number it cannot defend. The partition in
`expectation_origin_rows.jsonl` splits the 384 into four populations whose expectations have
**four different denominators**, three of which are circular. Any single "entity coverage %"
over all 384 is a figure against a list the project wrote itself, which is the exact failure
GAP-ENTITY_COVERAGE-004 was opened to name.

So: **one report, four sections, four denominators, and one of them honestly reported as
undefined.**

## 2. Denominators, per class

| class | rows | honest denominator | can it name a MISSING entity? |
|---|---|---|---|
| **A** EXPLICITLY_EXPECTED_BY_A_SOURCE | 161 | The external index's own headword set, scoped to entries whose body cites a Samhita: **2,532 folded headwords** of the Vedic Index's 3,834 entries / 3,588 distinct folded headwords. | **YES.** This is the only class that can. |
| **B** DERIVED_FROM_AN_INTERNAL_CURATED_REGISTRY | 127 | The curated file's own record count. **Circular**: the numerator and the denominator are the same list. | NO. It can only report "all curated rows are present", which is a tautology. |
| **C** DERIVED_FROM_CORPUS_INVENTORY | 79 | The measured attestation population — but the measurement ran over the **alias list we wrote**, so the denominator is again our own vocabulary. | NO, not for entity coverage. It CAN honestly report alias recall, which is a different question. |
| **D** PRODUCT_EXPECTATION | 17 | The benchmark's question set: 100 questions in V3_3, of which Q78 is the governing one. **Not a population of entities at all.** | NO. It reports "the surface asked, and the node now exists". |
| **E** UNSUPPORTED_LEGACY_EXPECTATION | 0 | n/a | n/a |

**Therefore the coverage report has exactly one real numerator/denominator pair, and it lives
in class A.** The other three sections must print their denominator's name and the sentence
"this denominator is the project's own list; a 100% here is not evidence of completeness."

## 3. The class-A query — the one that would have found trapu

```
D = { VEI headword h : the entry body for h cites a Samhita }        -- external, 2,532
R = { registry entity e : fold(sanskrit_segment(e.entity_key)) }      -- ours, 384
MISSING = D \ R
```

Concretely, once `expected_source` exists on the nodes:

```cypher
// the registry side of the diff, straight from the graph
MATCH (n:DomainEntity)
RETURN n.entity_key                  AS entity_key,
       n.expected_source             AS expected_source,
       n.expectation_origin          AS expectation_origin,
       n.externally_expected         AS externally_expected
```

and the missing side, which cannot come from the graph because the graph does not hold what it
lacks:

```
for h in D:
    if fold(h) not in R:
        emit { headword: h, vei_entry: L, vei_page: pc,
               samhita_loci: <parsed from the entry body>,
               attested_in_our_corpus: <count of Mantra whose SEARCH_DERIVATIVE text contains h>,
               verdict: MISSING_AND_ATTESTED   if attested_in_our_corpus > 0
                        MISSING_NOT_ATTESTED   otherwise }
```

`MISSING_AND_ATTESTED` is the row class that matters. It says: a published index says the
Samhitas name this, and **our own stored Sanskrit contains it**, and we have no node for it.
That is precisely the trapu case, and it needs no human to read anything.

### Alignment rule, stated so it can be audited

Our keys are ASCII, diacritic-free, `VG:CONCEPT:<SANSKRIT>-<GLOSS>`. The Vedic Index's
machine-readable headword is SLP1. Fold SLP1 to our convention:
`A I U -> A I U`, `f F -> R`, `x X -> L`, `E -> AI`, `O -> AU`, `K G C J T D P B -> KH GH CH JH TH DH PH BH`,
`Y N -> N`, `R -> N`, `w W q Q -> T TH D DH`, `S z s -> S`.
Match the whole key without hyphens first, then the longest hyphen-prefix join.

**This fold is lossy and the report must say so.** `S`, `z` and `s` all become `S`; `R` and
`n` both become `N`. Measured: **14 of the 200 matched rows** have more than one distinct SLP1
headword folding to the same string, and those 14 are **excluded from class A** rather than
guessed. They are listed in the rows file with `vei_fold_is_ambiguous: true`:
ASTAKA, BHARATA-TRIBE, DHRUVA-SPOON, GRAHA-SOMA-DRAWING, JANA-PEOPLE, KASA-COUGH, LAKSA-PLANT,
MASA-BEAN, MAYA-WILE, SALA-HOUSE-BUILDING, SURA-SPIRITUOUS-LIQUOR, VAPA-OMENTUM,
VRATA-ORDINANCE, YAVA-BARLEY. `MASA-BEAN` is the textbook case: masa (month) and maza (bean)
fold to the same six letters.

A further **25** matched rows are excluded because the fold resolves to more than one VEI
entry, or to more than one Samhita-citing entry, so the sense is not determined by the match
alone. Every class-A row therefore also carries
`vei_alignment_basis: "HEADWORD_LEXICAL_MATCH_SENSE_NOT_HUMAN_REVIEWED"`. The alignment is
lexical. 161 rows are aligned; **0 of them are human-reviewed for sense**, and the report must
print that, not hide it.

## 4. The scope limit that makes or breaks this design

**The Vedic Index is an index of names and realia, not of deities or abstract nouns.** Measured
against its 3,834 entries:

| our label | in VEI | our count | VEI coverage |
|---|---|---|---|
| Animal | 15 | 15 | **100%** |
| Place | 11 | 11 | **100%** |
| River | 8 | 8 | **100%** |
| Metal | 7 | 7 | **100%** |
| Weapon | 5 | 5 | **100%** |
| Tribe | 5 | 5 | **100%** |
| Crop | 5 | 5 | **100%** |
| Plant | 21 | 22 | 95% |
| Substance | 30 | 33 | 91% |
| Offering | 17 | 21 | 81% |
| Object | 32 | 41 | 78% |
| RitualRole | 12 | 20 | 60% |
| Condition | 20 | 36 | 56% |
| NaturalPhenomenon | 6 | 13 | 46% |
| PhilosophicalConcept | 5 | 13 | 38% |
| **Ritual** | **19** | **103** | **18%** |
| **Action** | **4** | **26** | **15%** |
| **Quality** | **0** | **3** | **0%** |

Verified absences that prove the scope limit, by exact headword probe on the TEI:
`agni` **absent**, `anna` **absent**, `amfta` (amrta) **absent** — while `yava`, `vrIhi`,
`aja`, `go`, `godAna`, `vAsas`, `rajju`, `kumBa` are all present. Macdonell and Keith left
mythology and religion to Macdonell's *Vedic Mythology*; the Index covers persons, places,
tribes, institutions and material things.

**Consequence for the report:** the class-A diff is valid for the **realia labels** (Animal,
Place, River, Metal, Weapon, Tribe, Crop, Plant, Substance, Offering, Object) and **must not be
run** as a completeness figure over Ritual, Action, PhilosophicalConcept, Quality or State. For
those, the report prints `denominator: NONE_AVAILABLE` and names the reason. Reporting
"Ritual is 18% covered by the Vedic Index" would be a figure about Macdonell's editorial scope,
not about our registry.

## 5. Two further denominators that are real but narrow

**(a) An in-corpus enumeration verse.** `VG:YV:VSM:A18:V013` names six metals in one line. A
verse that enumerates is a declared expectation the corpus itself publishes, and its
denominator is exactly its own list length. This is the honest form of class C: not "our alias
scan found N", but "this verse lists six things and we hold k of them".

**(b) The Srautasutra rtvij schema of sixteen.** 20 of the 384 carry
`denominator_schema: SRAUTASUTRA_RTVIJ_SCHEMA_OF_SIXTEEN`, and 9 carry the repo's only external
citation, `existence_evidence_citation: "SankhSS 13.14.1"` with
`existence_evidence_translation_citation: "W. Caland, Sankhayana-Srautasutra"`. That is a real
external declared expectation with a real denominator (sixteen) — but it declares a
**Srautasutra** population, not Samhita content, and the node's own
`denominator_schema_note` says so: "The sixteen officiants are a SRAUTASUTRA schema, not a
Samhita one. Any completeness figure over sixteen is a figure against that schema and is
labelled so." It therefore does **not** satisfy class A's test ("names this as something the
Samhitas contain") on its own, and the rows file records the Caland citation in
`node_existence_evidence_citation` rather than in `expected_source`.

## 6. Worked example: the metals

### 6.1 The in-corpus declared list, VSM 18.13

`VG:YV:VSM:A18:V013` names hiranya, ayas, syama, loha, sisa, trapu.

| metal | in the registry? | key |
|---|---|---|
| hiranya | YES | VG:CONCEPT:HIRANYA-GOLD |
| ayas | YES | VG:CONCEPT:AYAS-METAL |
| syama | YES | VG:CONCEPT:SYAMA-DARK-METAL |
| loha | YES | VG:CONCEPT:LOHA-COPPER |
| sisa | YES | VG:CONCEPT:SISA-LEAD |
| trapu | YES | VG:CONCEPT:TRAPU-TIN |

**6 of 6. Zero missing.** The `:Metal` class holds seven nodes — those six plus
`VG:CONCEPT:RAJATA-SILVER`. So this denominator **closes**, and if it were the only one used
the registry would look complete. That is the trap, and it is why one worked example is not
enough.

### 6.2 The external list, and what it finds that 6.1 cannot

VEI entries whose body contains the word "metal": **22**. Of those, **8 are in the registry**
(Ayas, Ayudha, Hiranya, Loha, Masa, Syama, Trapu, Varman) and **14 are not**:
Abhri, Dhmatr, Kamsa, Karmara, Karsnayasa, Kavaca, Krsnayasa, Kusa, Lohayasa, Lohita,
Lohitayasa, Pavi, Pavira, Prakasa.

Filter those 14 by the class-A rule (the VEI entry must cite a Samhita) and then measure each
against our own stored Sanskrit. The result, all machine-derived:

| VEI headword | VEI's own Samhita citation, verbatim | distinct Mantras in OUR corpus whose text contains it | registry node | verdict |
|---|---|---|---|---|
| **Lohita** | "used as a neuter substantive in the Atharvaveda (xi. 3, 7) to denote a metal, presumably 'copper'" | **15** — incl. AVS 11.3.7, AVS 1.17.1, AVS 9.8.1, RV 10.85.28 | **none** | **MISSING_AND_ATTESTED** |
| **Karmara** | "the 'smith,' is several times mentioned with approval in the Vedic Samhitas. Rv. x. 72, 2; Av. iii. 5, 6; ... Vajasaneyi Samhita, xvi. 27; xxx. 7" | **4** — RV 10.72.2, AVS 3.5.6, VSM 16.27, VSM 30.7 | **none** | **MISSING_AND_ATTESTED**, and the four loci round-trip **4 / 4** |
| Lohitayasa | "the variant of Loha in the Maitrayani (ii. 11, 5; iv. 4, 4) and Kathaka (xviii. 10) Samhitas" | 0 (we hold neither MS nor KS) | none | MISSING, OUT OF OUR CORPUS SCOPE |
| Kamsa | "'pot or vessel of metal,' occurs in the Atharvaveda. Av. x. 10, 5" | 0 on the literal fold | none | MISSING, NOT MATCHED — needs a sandhi-tolerant probe before it can be claimed |
| Karsnayasa, Krsnayasa | "a word found in the Upanisads" / "Chandogya Upanisad" | n/a | none | CORRECTLY EXCLUDED — not a Samhita claim |

### 6.3 Why this is the proof the closure test asks for

**Lohita is trapu's twin, one verse earlier, and it is still missing today.**
`VG:AV:SAU:K11:S003:V007`, PRIMARY_TEXT, from our own graph:

> `śyāmám áyo 'sya māṃsā́ni lóhitam asya lóhitam ||7||`

and the next verse, `VG:AV:SAU:K11:S003:V008`:

> `trápu bhásma háritaṃ várṇaḥ púṣkaram asya gandháḥ ||8||`

The registry holds `SYAMA-DARK-METAL` and `AYAS-METAL` from verse 7 and `TRAPU-TIN` from verse
8. It does not hold `lohita`, which occurs **twice in verse 7** and in **15 mantras** overall.
Nobody read the text to find that. The VEI headword set, the fold, and one containment query
over `SEARCH_DERIVATIVE` text produced it.

`Karmara` is the cleaner demonstration because its verification is exact: VEI prints four
Samhita loci and all four resolve to mantras we hold, with no fold tolerance needed.

## 7. Report shape

```
SECTION 1  CLASS A - external expectation, Samhita-scoped, realia labels only
  denominator      2,532 VEI Samhita-citing headwords
  restricted to    the realia labels (see the scope table)
  registry present <n>
  MISSING_AND_ATTESTED   <rows>   <- the actionable list
  MISSING_NOT_ATTESTED   <rows>   <- external says yes, our corpus does not contain it
  fold_ambiguous_excluded  14
  multi_entry_excluded     25
  sense_human_reviewed      0     <- must be printed

SECTION 2  CLASS A - labels with NO external denominator
  Ritual, Action, PhilosophicalConcept, Quality, State
  denominator      NONE_AVAILABLE
  reason           the Vedic Index excludes mythology and abstract nouns; agni, anna and
                   amrta are absent from it by editorial scope, not by Vedic absence

SECTION 3  CLASS B / C / D - circular denominators
  For each: denominator name, row count, and the fixed sentence
  "this denominator is the project's own list; 100% here is not evidence of completeness"

SECTION 4  NARROW DENOMINATORS THAT DO CLOSE
  VSM 18.13 metals            6 / 6
  Srautasutra sixteen rtvij   <k> / 16, labelled SRAUTASUTRA and not Samhita

SECTION 5  CLASS E
  0 rows. The criterion and the near-miss stratum are printed, not omitted.
```

## 8. What this design deliberately does not do

- It does not compute a single "entity coverage" percentage. There is no denominator for one.
- It does not run the class-A diff over Ritual or Action. The Index's silence there is
  editorial, and treating it as absence would invert the measurement.
- It does not treat a fold collision as a match. 14 rows are excluded by name.
- It does not claim sense agreement. 161 lexical alignments, 0 human-reviewed, printed as such.
- It does not use the Caland/SankhSS citation as a Samhita expectation, because the node's own
  `denominator_schema_note` forbids exactly that.
