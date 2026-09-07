# V3 508 review queue triage

Engineering diagnostics, not Vedic expertise, HUMAN_GOLD, or canonical truth. All existing output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. No extraction was performed in this audit.

All 50 cases were inspected. **19** exhibit a concrete systemic blocker;
**31** do not block individually. Blocking labels point to existing
engineering failures, not expert approval requirements. A nonblocking label is not semantic acceptance.
No EVIDENCE_PACKET_BUG was established: bad spans are generated evidence anchors, not corrupted
packet IDs. Canonical ID membership is intact, but valid IDs can still be attached to the wrong relation.

Primary category counts: {"CANONICAL_ENTITY_RISK": 12, "EXPECTED_MODEL_UNCERTAINTY": 1, "OBJECT_GRANULARITY": 3, "ONTOLOGY_GAP": 17, "PHILOLOGY_REQUIRED": 3, "PREDICATE_BOUNDARY": 5, "SAFE_REVIEW_ONLY": 5, "TRANSLATION_AMBIGUITY": 2, "TYPE_BOUNDARY_RISK": 2}.

| Case | Mantra | Primary category | Secondary tags | Gate | Blockers | Evidence-based diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| REV-01 | RV 10.170.1 | PREDICATE_BOUNDARY | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 B02 | May the God drink does not request offspring; guards our offspring is descriptive. In person is not human. |
| REV-02 | RV 9.4.9 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | Human worshippers are evidenced, but gap span points into Pavamana; no-claim itself may remain cautious. |
| REV-03 | RV 1.137.3 | CANONICAL_ENTITY_RISK | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Come nigh addresses Mitra and Varuna, while extractor invokes the Soma to be drunk; milk verbs also become substance. |
| REV-04 | RV 9.86.38 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | Human collective is valid, but gap span points inside Pavamana; wealth and strength requests are directly phrased. |
| REV-05 | RV 8.35.8 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | O Asvins is the address; Soma sought for drinking and accompanying Surya become INVOKES targets. |
| REV-06 | RV 8.35.9 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Same Asvin address is misbound to Soma/Surya; added oblation supports an independent offering difference. |
| REV-07 | RV 8.35.16 | PREDICATE_BOUNDARY |  | DOES_NOT_BLOCK_FULL_RUN |  | Commands to slay and drive away disease raise request/event boundary; retained event is review-sensitive. |
| REV-08 | RV 8.35.18 | PREDICATE_BOUNDARY |  | DOES_NOT_BLOCK_FULL_RUN |  | Give strength is a real wording addition; shared commands need event/request review, not enforced equality. |
| REV-09 | RV 8.36.4 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | O Satakratu, drink Soma addresses the drinker; INVOKES SOMAH confuses drink with addressee. |
| REV-10 | RV 8.36.6 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Glorify the Atris' hymn and drink Soma does not praise/invoke Soma; verse-wide cue scope fails. |
| REV-11 | RV 8.1.17 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Human operators, milk and waters are explicit; ritual/substance detail is reviewable. |
| REV-12 | RV 9.20.2 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | Singing-men are human recipients but span points inside Pavamana; send action is directly supported. |
| REV-13 | RV 9.87.4 | CANONICAL_ENTITY_RISK | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | O Indra receives address; Soma is thine own drink, not a second invoked target; Free-giver is not human patron. |
| REV-14 | RV 9.87.9 | CANONICAL_ENTITY_RISK | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Indra is a companion, not necessarily praised; Giver is addressed Soma, not an unmodeled human patron. |
| REV-15 | RV 10.97.7 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Human patient is explicit; rich in Soma substance identity may need domain review without structural leakage. |
| REV-16 | RV 1.122.8 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | Donor/men are clear, but span man comes from many; no-claim does not justify canonicalizing a chief. |
| REV-17 | RV 1.127.2 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Priest of men includes humans; unnamed divine identity and archaic address can remain unclaimed. |
| REV-18 | RV 4.19.10 | PHILOLOGY_REQUIRED | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Elliptical grammar and wise-man addressee need reading; no structural failure in withholding assertions. |
| REV-19 | RV 7.32.20 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Active man is human; Much-invoked is descriptive epithet, not necessarily a fresh invocation. |
| REV-20 | RV 8.6.37 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Human invokers are clear; unnamed Best slayer identity remains unresolved. |
| REV-21 | RV 8.21.14 | TRANSLATION_AMBIGUITY | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Wealthy man, scorners and Father simile leave target scope open; no invented identity. |
| REV-22 | RV 8.46.27 | PHILOLOGY_REQUIRED | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Glorious one, Nahup and more devout man need referent resolution; retain opaque uncertainty. |
| REV-23 | RV 9.45.6 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Worshipping human is explicit; Flow and heroic strength are not automatically a strength request. |
| REV-24 | RV 10.18.8 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | Woman and husband are clear, but stored span is only man inside woman; funeral interpretation is not needed for this diagnostic. |
| REV-25 | RV 10.27.13 | PHILOLOGY_REQUIRED | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Riddle participant and pronouns are obscure; withholding a canonical interpretation is appropriate. |
| REV-26 | RV 10.39.11 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Man is beneficiary; corrupted come u on translation deserves source review, not invented correction. |
| REV-27 | RV 10.107.10 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Human donor is supported; lake/palaces are similes and need no forced place assertions. |
| REV-28 | RV 10.118.1 | EXPECTED_MODEL_UNCERTAINTY | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | No-claim omits slayest wording; isolated omission remains review, and cannot validate checklist completeness. |
| REV-29 | RV 1.23.20 | OBJECT_GRANULARITY |  | DOES_NOT_BLOCK_FULL_RUN |  | Extra sentence Waters hold all medicines explains medicine detail; Soma speaker versus substance remains review-sensitive. |
| REV-30 | RV 1.133.6 | PREDICATE_BOUNDARY | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Thunder-armed epithet becomes storm; distinguish figurative description from actual phenomenon without ontology rewrite. |
| REV-31 | RV 5.17.1 | TYPE_BOUNDARY_RISK | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Sacrifice may denote act rather than offered object; permitted OFFERING_REF shape alone does not settle semantic role. |
| REV-32 | RV 8.35.7 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | O Asvins address again produces Soma and Surya invocations: repeated target-scope failure. |
| REV-33 | RV 8.36.5 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Satakratu is addressed; Soma is drunk, not invoked. Same failure as neighboring verses. |
| REV-34 | RV 9.34.2 | OBJECT_GRANULARITY |  | DOES_NOT_BLOCK_FULL_RUN |  | Soma juice normalized as meath is a granularity/translation diagnostic; recipient list differs from next pair member. |
| REV-35 | RV 9.39.2 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Food for man, rain and heaven are supplied; send normalizes bringing and is reviewable. |
| REV-36 | RV 9.65.20 | PREDICATE_BOUNDARY |  | DOES_NOT_BLOCK_FULL_RUN |  | Water-winner epithet drives water/phenomenon claims; preserve candidate review for figurative scope. |
| REV-37 | RV 10.9.6 | OBJECT_GRANULARITY |  | DOES_NOT_BLOCK_FULL_RUN |  | Shorter Waters passage lacks explicit medicines sentence; broad comparison is partial for explainable reason. |
| REV-38 | RV 10.41.1 | CANONICAL_ENTITY_RISK | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | The invoked/described Car is not the lexical Dawn entity; verse-wide descriptive cue attaches DESCRIBES to Dawn. |
| REV-39 | RV 10.151.4 | TYPE_BOUNDARY_RISK | ONTOLOGY_GAP | DOES_NOT_BLOCK_FULL_RUN |  | Gods and men who sacrifice states an act, not automatically a thing offered; keep role boundary review. |
| REV-40 | RV 10.58.4 | SAFE_REVIEW_ONLY |  | DOES_NOT_BLOCK_FULL_RUN |  | Four quarters differs from Yama's Son; its no-claim does not share the false offspring assertion. |
| REV-41 | RV 10.58.5 | SAFE_REVIEW_ONLY |  | DOES_NOT_BLOCK_FULL_RUN |  | Sea wording differs from waters/plants; absence of an ontology head is not evidence fabrication. |
| REV-42 | RV 10.58.6 | SAFE_REVIEW_ONLY |  | DOES_NOT_BLOCK_FULL_RUN |  | Beams of light differ from waters/plants; withheld claim is not itself a systemic error. |
| REV-43 | RV 10.58.9 | SAFE_REVIEW_ONLY |  | DOES_NOT_BLOCK_FULL_RUN |  | Mountain heights differ from waters/plants; local no-claim does not justify global semantic equality. |
| REV-44 | RV 10.58.11 | SAFE_REVIEW_ONLY |  | DOES_NOT_BLOCK_FULL_RUN |  | Distant realms remain vague; opaque spatial handling is acceptable. |
| REV-45 | RV 8.35.5 | TRANSLATION_AMBIGUITY |  | DOES_NOT_BLOCK_FULL_RUN |  | Sarya/Surya and Come/Conie source variants explain lexical sensitivity; no silent text repair. |
| REV-46 | RV 8.35.6 | CANONICAL_ENTITY_RISK | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | O Asvins still receives the address; Surya becomes INVOKES because its name and O co-occur. |
| REV-47 | RV 1.13.11 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Giver of the oblation is a donor role; existing gap is safer than forced identity. |
| REV-48 | RV 1.35.5 | ONTOLOGY_GAP | ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B02 | All men is supported but span hits manifested; ID-valid evidence is not enough. |
| REV-49 | RV 1.43.6 | ONTOLOGY_GAP |  | DOES_NOT_BLOCK_FULL_RUN |  | Human and livestock beneficiaries explicitly receive health; person typing can be deferred safely. |
| REV-50 | RV 1.51.9 | CANONICAL_ENTITY_RISK | ONTOLOGY_GAP, ARCHITECTURE_BUG | BLOCKS_FULL_RUN | B01 | Vamra when glorified drives PRAISES Indra elsewhere in the verse; laudatory target is misbound. |

## Existing 20 expert cases

The prior 20-case V3 queue was inspected alongside its 508 stability records. All remain unresolved
expert diagnostics; none is human gold. The two canonical-scope examples 9.87.9 and 10.89.8 must
also be tracked as engineering target-binding risks; 10.27.13 remains a riddle/philology issue.
The expert queue is not an exhaustive engineering risk inventory. No expert answer was invented.

| Mantra | In 508 | V3 stable | Existing status |
| --- | --- | --- | --- |
| VG:RV:SAK:M09:S068:V010 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S005:V014 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S022:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S030:V003 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S022:V014 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S001:V017 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S108:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M02:S008:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M06:S068:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S087:V009 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S074:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S104:V005 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S035:V009 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M02:S017:V005 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M01:S094:V013 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M06:S013:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S089:V008 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S034:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S060:V011 | True | True | EXPERT_PHILOLOGY_REQUIRED |
| VG:RV:SAK:M10:S027:V013 | True | True | EXPERT_PHILOLOGY_REQUIRED |
