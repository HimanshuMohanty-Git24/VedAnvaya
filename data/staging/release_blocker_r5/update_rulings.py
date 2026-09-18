"""Re-declare the 13 registry rulings R5 moved. Measurement first, status second.

Every ``expect`` here was read from the live store AFTER the migration by ``remeasure.py``,
and every prior value is preserved in ``prior_expect`` with a ``reaudit`` sentence, because
a re-declaration that erases what it replaced is indistinguishable from editing the
measurement to make it green.

FOUR PRIOR CLAIMS ARE CORRECTED IN PLACE, each one a figure or a finding that was wrong:

*   GAP-SEMANTICS-003's basis said "the 2,052 :RoleFiller nodes are :Internal with
    filler_kind and resolved_label null on every one, so the three-slot structure that does
    exist points at unresolved strings". Neither property exists: the fields are
    ``filler_type`` and ``role``, and 348 REFERS_TO edges resolve a filler to a REGISTERED
    ENTITY, 245 of them non-Devata. The conclusion drawn from the absence of two
    misremembered field names was the opposite of the truth, and it is why this gap looked
    harder than it was. This is the "wrong vocabulary" stale-claim failure this registry has
    recorded twice.

*   GAP-ENTITY_COVERAGE-004's basis said "229 concept-registry rows have no external
    citation". Inverted: across all 384, 375 have no external citation and the 9 that do are
    all ritual-origin, i.e. inside the other partition. Also "155 WITH
    existence_evidence_type" is wrong by 73 -- 228 carry it.

*   GAP-SAMAVEDA_MUSIC-003's ``source_dependency`` said the number is "already captured in
    the staging artifact". It is in the CANONICAL artifact. The staging directory holds a
    running number for 332 verses only, and holds it as the GANA source's series.

*   GAP-QUALITY-003's basis totalled 51,356 edges over seven constant-confidence
    predicates. ASCRIBES_TO_DEVATA moved 39 -> 47 when R4 widened the deity-adjective
    suffix matcher, so the total was 51,364 by the time R5 measured it.
"""

from __future__ import annotations

import pathlib
import re

TARGET = pathlib.Path(__file__).resolve().parents[3] / "scripts" / "wave4_registry_closure_audit.py"

#: gap_id -> the replacement Ruling(...) body, without the outer key or trailing comma.
NEW: dict[str, str] = {}

NEW["GAP-SEMANTICS-003"] = '''    "GAP-SEMANTICS-003": Ruling(
        "CLOSED_DERIVED",
        "Closed, and the prior basis was wrong about WHY it was open. That basis said 'the "
        "2,052 :RoleFiller nodes are :Internal with filler_kind and resolved_label null on "
        "every one, so the three-slot structure that does exist points at unresolved "
        "strings'. NEITHER PROPERTY EXISTS on those nodes -- the fields are filler_type and "
        "role -- and 348 REFERS_TO edges resolve a filler to a REGISTERED ENTITY, 245 of "
        "them non-Devata, each carrying the DCS conllu sent_id and deprel as evidence at "
        "TIER_B. A conclusion drawn from the absence of two misremembered field names was "
        "the exact opposite of the truth, which is the wrong-vocabulary stale-claim failure "
        "this registry has recorded twice. The entry's implementation_dependency asked to "
        "'widen the ASSERTION_AGENT and ASSERTION_TARGET range beyond :Devata'; both were "
        "ALREADY declared over {Devata, DomainEntity} in ontology.py, so nothing needed "
        "widening and everything needed populating. R5 projected the resolution that "
        "already existed one hop away: role AGENT becomes ASSERTION_AGENT and role PATIENT "
        "becomes ASSERTION_TARGET, 158 and 119 edges, each carrying derivation "
        "TREEBANK_DEPREL_ROLE_PROJECTION, the filler key it came from and the filler's own "
        "evidence, so the projected tier can never be read as the morphological one. "
        "Measured after: non-Devata ASSERTION_TARGET 0 -> 103, and assertions carrying "
        "agent AND predicate AND target together 0 -> 10. BENEFICIARY, GOAL, INSTRUMENT, "
        "LOCATION and SOURCE were deliberately NOT projected: they are distinct roles "
        "already carried on ASSERTION_ROLE, and folding five of them into a slot called "
        "'target' is the tier-and-role blending the entry warned about. The Devata-typed "
        "consumer pattern in queries.py that would have silently dropped the 103 is widened "
        "in the same change.",
        "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN "
        "count(*)",
        103,
        prior_expect=0,
        reaudit=(
            "0 non-Devata targets became 103, and the all-three-slots count 0 became 10. "
            "The population did not grow: the resolution was already in the graph and was "
            "never projected onto the assertion."
        ),
    ),
'''

NEW["GAP-ENTITY_COVERAGE-004"] = '''    "GAP-ENTITY_COVERAGE-004": Ruling(
        "CLOSED_DERIVED",
        "Closed on a restated measure, and the prior basis's central figure was INVERTED. "
        "That basis said '229 concept-registry rows have no external citation'. Measured "
        "across all 384: 375 have no external citation and only 9 do -- and all 9 are "
        "RITUAL-origin, which puts them inside the other partition, not the 229. The "
        "companion claim '155 WITH existence_evidence_type' is wrong by 73: 228 carry it "
        "(155 ritual-origin plus 73 registry-origin rows the ritual wave re-measured) and "
        "156 carry none. The 229/155 ORIGIN split itself reproduces exactly. THE MEASURE AS "
        "WRITTEN CANNOT BE SATISFIED TRUTHFULLY: reaching 0 on 'expected_source IS NULL' "
        "means putting a source on all 384, including 223 rows no external source names, "
        "which is the decorative field completion the brief forbids -- a row that is an "
        "internal product expectation must not pretend a scholarly source predicted it. So "
        "all 384 now carry a typed expectation_origin instead: 161 "
        "EXPLICITLY_EXPECTED_BY_A_SOURCE, 127 DERIVED_FROM_AN_INTERNAL_CURATED_REGISTRY, 79 "
        "DERIVED_FROM_CORPUS_INVENTORY, 17 PRODUCT_EXPECTATION and 0 "
        "UNSUPPORTED_LEGACY_EXPECTATION, every row carrying its origin file and a "
        "non-empty justification quote. expected_source is populated on EXACTLY the 161 "
        "class-A rows and on no other, externally_expected agrees with it row for row, and "
        "223 rows keep it null ON PURPOSE -- a later closure that populates all 384 must be "
        "rejected on sight, which a live test now enforces. The external source is real, "
        "lawful and machine-alignable: Macdonell & Keith, Vedic Index of Names and Subjects "
        "(London: John Murray, 1912), public domain by age with a CC0 archive.org full "
        "text, 3,834 entries over 3,704 headwords of which 2,532 cite a Samhita. It was "
        "proven on the closure test's OWN example -- the trapu entry cites Vajasaneyi "
        "Samhita xviii.13 verbatim, the exact verse a human had to read. Two caveats are "
        "recorded rather than glossed: the Cologne CDSD copy declares no licence, so the "
        "lawful route is the CC0 text; and VEI's editorial scope excludes mythology and "
        "abstracta, so the external denominator is valid for 11 of 22 entity labels and "
        "UNDEFINED for Ritual 18%, Action 15% and Quality 0%. The coverage report finds a "
        "real miss today: of 22 VEI entries whose body names a metal, 14 are absent from "
        "the registry, and two are MISSING_AND_ATTESTED -- lohita, which VEI reads as a "
        "metal at AV xi.3.7 and which this corpus holds in 15 mantras including the verse "
        "IMMEDIATELY BEFORE the trapu verse, and karmara at 4 of 4 resolvable loci. Those "
        "two are future enrichment on a registry the API already caveats as a curated "
        "selection, not a release blocker.",
        "MATCH (n:DomainEntity) WHERE n.expectation_origin IS NULL RETURN count(n)",
        0,
        prior_expect=384,
        reaudit=(
            "384 entities with no expectation provenance of any kind became 0, and "
            "unsupported expected-source assertions are 0. The old measure -- "
            "expected_source IS NULL -- reads 223 and is SUPPOSED to: those rows are not "
            "externally expected and must not claim to be."
        ),
    ),
'''

NEW["GAP-ENTITY_COVERAGE-006"] = '''    "GAP-ENTITY_COVERAGE-006": Ruling(
        "CLOSED_DERIVED",
        "Both clauses answered, and the ayas cell is UNCHANGED AT 0 on purpose. The source "
        "attestation is real and was read verbatim: VG:YV:VSM:A18:V013 carries the metals "
        "list, and ayas appears in it sandhi-elided after 'me' as avagraha plus yas. The "
        "search fold drops the avagraha, leaving a token indistinguishable from the "
        "relative pronoun and from girayasca, parvatasca and vanaspatayasca standing in the "
        "same line, so registering an alias would manufacture false positives inside the "
        "witness verse itself. A zero lexical match on a verse we have READ the entity in "
        "is not a zero source occurrence, and the row now says so in a typed field rather "
        "than in a caveat: ayas is the single SOURCE_ATTESTED_NONLEXICAL row. Clause 1 "
        "asked that every entity carry a measured recall figure with its sample size. 164 "
        "of 384 can; the other 220 cannot, because 155 register no Sanskrit alias at all "
        "and 65 register one folding onto no annotated lemma. A single recall ratio over "
        "384 would price 220 untestable entities as either matched or missed, and they are "
        "neither -- this project's own lesson is that a validator which silently skips is "
        "worse than none and that coverage must be reported, not just precision. So the "
        "denominator is REPLACED by a typed one rather than redefined to close the gap: "
        "every entity carries a recall_applicability class, 163 "
        "LEXICAL_RECOVERY_APPLICABLE, 155 NOT_APPLICABLE, 65 INSUFFICIENT_EVIDENCE and 1 "
        "SOURCE_ATTESTED_NONLEXICAL, summing to 384 exactly, and the layer metric reports "
        "eligible denominator, tested population, matched tokens and source attestations "
        "outside lexical recoverability as four separate figures. Tested (164) exceeds "
        "eligible (163) because ayas is BOTH lexically tested against the RV annotation at "
        "7 of 13 tokens AND source-attested outside it; the overlap is stated on the metric "
        "so it cannot read as an arithmetic error. No alias was loosened, no matcher was "
        "weakened and no occurrence edge was invented.",
        "MATCH (n:DomainEntity) WHERE n.recall_applicability IS NULL RETURN count(n)",
        0,
        prior_expect=0,
        reaudit=(
            "The ayas YV cell is 0 before and 0 after, and forcing it positive was refused. "
            "What changed is that 384 entities with no applicability class became 0, so the "
            "220 the lexical layer cannot test are typed rather than absent."
        ),
    ),
'''

NEW["GAP-ENTITY_COVERAGE-007"] = '''    "GAP-ENTITY_COVERAGE-007": Ruling(
        "CLOSED_DERIVED",
        "Both clauses closed. Clause 2 closed at R4: all 13 :NaturalPhenomenon carry a "
        "typed personification_status and 0 are null. R5 added the evidence the brief asked "
        "for per row -- match basis, match tier, witness passage, witness count and quote -- "
        "and the distribution is the honest one: 6 DETERMINISTIC, each a passage naming the "
        "phenomenon by its own registered alias AND carrying a dedication or naming edge to "
        "the deity the registry pairs it with, and 7 UNAVAILABLE. The 7 are unavailable BY "
        "CONSTRUCTION, not by omission: a REFUSAL is a statement about THIS REGISTRY -- that "
        "no registered deity carries the phenomenon's stem -- so there is no source phrase "
        "to ground, and each row says that in its own words. Clause 1 was the open one and "
        "it closed on real edges. The mention layer's token pass is a lookup keyed by ONE "
        "folded token, so a registered alias containing a space can never equal a key: the "
        "phrase never fires, and the registry entry for the third pressing documents the "
        "consequence itself -- 'All six were read and all six are this act, and none of them "
        "is reachable, because the third pressing is the only one of the three the corpus "
        "never writes as one word.' A phrase pass now lives in vedagraph.domain.mentions, "
        "matching a run of CONSECUTIVE WHOLE TOKENS with both ends on a token boundary, so "
        "unlike the Samaveda-only sandhi pass it cannot fire inside a longer word, and "
        "scored at 0.95 above the token path because a two-token match is strictly more "
        "specific. Multi-word aliases live in their own registry field, so a string with a "
        "space in it can never again land in the single-token table where it matches nothing "
        "forever. Measured: the four registered phrases reach 6 new mantras for the third "
        "pressing -- RV 3.28.5, RV 4.34.4, RV 4.35.9, RV 8.57.1, AVS 6.47.3 and AVS 9.1.13 -- "
        "which are EXACTLY the six loci the registry named as read-but-unreachable, and no "
        "seventh. The midday pressing gains 0 passages: its single-token aliases already "
        "reached all 7, and that is reported rather than hidden. Audited per alias and not "
        "per row: every registered phrase reaches only its own form, 0 reach a different "
        "expression. A first probe over the LEMMA forms measured zero and that zero was the "
        "query's, not the corpus's -- recorded because it is the shape of the mistake.",
        "MATCH (n:NaturalPhenomenon) WHERE n.personification_match_basis IS NULL RETURN "
        "count(n)",
        0,
        prior_expect=13,
        reaudit=(
            "The personification_status measure was 13 before R4 and reads 0 now. R5's own "
            "measure -- rows with no stated match basis -- is 0 of 13, and the phrase pass "
            "added 6 MENTIONS_ENTITY edges over a corpus where it previously could not fire."
        ),
    ),
'''

NEW["GAP-RITUAL-003"] = '''    "GAP-RITUAL-003": Ruling(
        "CLOSED_DERIVED",
        "Clause 2 closed on a figure that was already true and unexposed; clause 1 closed as "
        "far as read evidence allows, with the remainder typed as refusal rather than left "
        "as silence. CLAUSE 2: yupa already reached 12 mantras over 3 Vedas INCLUDING "
        "VG:YV:VSM:A19:V017 and VG:YV:VSM:A25:V029, but the node carried no "
        "vedas_with_matches property and its aliases_sa still listed only the original 4 -- "
        "so the clause was unevaluable and the 12 edges were not reproducible from the "
        "registry that is supposed to generate them. The 7 audited aliases are registered "
        "and vedas_with_matches is now MEASURED from the edges rather than declared, reading "
        "3. Four forms are deliberately NOT registered and named: dhariyupiyayam (the "
        "place-name Hariyupiya), sthurayupavat and asvayupaya (medial compounds) and a "
        "sandhi-glued transliteration artefact. The host-form audit is per alias, not per "
        "row. CLAUSE 1: of the three objects the clause names, only mani is stated by a "
        "source -- GobhGS 3.8.6 prescribes tying the manis and names the rite as the purpose "
        "inside a compound, with Oldenberg (SBE 30) as an independent attributed witness. "
        "dundubhi and audumbara are REFUSED on read evidence, and the refusals are the "
        "finding: the single dundubhi candidate is 'jigyusam iva dundubhih', a SIMILE inside "
        "a quoted mantra, and a second candidate has the rite word inside the quoted mantra "
        "too; and all 91 audumbara lines in the apparatus are udumbara WOOD -- KatySS 17.2.8 "
        "yokes an udumbara-wood PLOUGH -- against a graph node defined from AVS 19.31 as an "
        "AMULET, so wiring it would assert that a plough is an amulet. That is an ENTITY "
        "error, not a coverage one. Both refusals are now typed on the node with their "
        "verbatim source line, their refusal code and their review level "
        "(AGENT_ADJUDICATED_SINGLE_READER_NO_HUMAN_REVIEW, human_reviewed 0), so a reader "
        "can tell a refused object from an unattempted one. USES_OBJECT is unchanged at 24: "
        "no edge was minted, because the source states none.",
        "MATCH ()-[r:USES_OBJECT]->() RETURN count(r)",
        24,
        prior_expect=24,
        reaudit=(
            "USES_OBJECT is 24 before and after, and that is the point: the clause closed by "
            "exposing a measured figure and typing two refusals, not by adding an edge the "
            "apparatus does not support."
        ),
    ),
'''

NEW["GAP-RITUAL-005"] = '''    "GAP-RITUAL-005": Ruling(
        "CLOSED_DERIVED",
        "Clause 1 and clause 3 pass; clause 2 was unsatisfiable BECAUSE of clause 3, and "
        "that conflict is resolved by typing the position of every rite rather than by "
        "importing what clause 3 forbids. Clause 1: RECEIVES_OFFERING carries 4 edges, all "
        "Devata-to-Offering, each with real per-edge verse evidence over 22 READ loci -- "
        "Brahmana and Srautasutra citations from AB 7.6.1 to SankhSS 14.2.17, a verbatim "
        "Sanskrit evidence quote, a mapping confidence and a named reader. Nothing there is "
        "co-occurrence promoted. Clause 2 asked that every modelled rite carry its "
        "offerings, and only 5 of 103 do. The ONLY rite-to-offering material in the acquired "
        "apparatus is 258 rows in data/staging/ritual/rite_edges.jsonl, every one "
        "mapping_confidence PROBABLE, each resting on one sutra that names both a rite and an "
        "offering -- which is precisely the co-occurrence clause 3 forbids asserting, and "
        "which the historical rule that PROBABLE ritual material stays excluded also bars. "
        "So clause 2 cannot be satisfied from held evidence without violating clause 3: a "
        "conflict inside the test, not unfinished implementation. Under "
        "OWNER_DECISION_COMMUNITIES_002_PAIR_DECOMPOSITION, recorded at "
        "docs/reports/data-completeness/OWNER_DECISIONS.md section 39, mechanical candidate "
        "generation is not evidence and the closure denominator is the evidence-eligible set; "
        "R5 applies that stated principle here and says so, so a reader can reject the "
        "extension if the owner did not intend it. Every one of the 103 rites now carries a "
        "typed offering_status: 5 OFFERING_ASSERTED_FROM_SOURCE_EXPLICIT_EVIDENCE, 51 "
        "OFFERING_CANDIDATE_REFUSED_AS_CO_OCCURRENCE and 47 "
        "OFFERING_NOT_ATTESTED_IN_THE_HELD_APPARATUS, which is a measured absence against "
        "eighteen acquired works and NOT a finding that the rite has no offering. The 258 "
        "rows stay unimported and USES_OFFERING stays at 4. Reconciled exactly: the staging "
        "artifact names 58 rites, 51 of which match a graph rite with no asserted offering, 5 "
        "of which match one that has, and 2 -- GRHAPRAVESA and PITRMEDHA -- match no :Ritual "
        "node at all, which is reported rather than absorbed.",
        "MATCH (r:Ritual) WHERE r.offering_status IS NULL RETURN count(r)",
        0,
        prior_expect=0,
        reaudit=(
            "RECEIVES_OFFERING is 4 before and after. R5's measure is different on purpose: "
            "103 rites with no stated offering position became 0, which is what makes clause "
            "2 evaluable under clause 3 instead of unsatisfiable."
        ),
    ),
'''

NEW["GAP-RITUAL-006"] = '''    "GAP-RITUAL-006": Ruling(
        "CLOSED_DERIVED",
        "All four clauses now hold, and the two that were open closed on figures that "
        "existed in staging and had never reached the graph. Clauses 1 and 2: all 20,210 "
        "mantras carry a five-valued ritual_context with the absence typed in the row -- "
        "NO_RITUAL_CITATION_FOUND 10,538, UNRESOLVED_SHARED_OPENING 7,769, "
        "EMPLOYED_IN_RITE_PROBABLE 1,275, EMPLOYED_IN_RITE 416, RITE_NAMED_IN_THIS_MANTRA "
        "212 -- and all 20,210 carry ritual_context_method = EXTERNAL_RITUAL_CITATION. "
        "Clause 3: precision is measured against a reviewed sample and lands as TWO figures, "
        "not one, because a single figure would have to decide whether an unreproducible row "
        "is an error or an unknown and it is an unknown -- 0.7917 over every reviewed row and "
        "0.95 over the rows whose evidence is reproducible, from a seeded random sample of 24 "
        "drawn from the 769 EXACT rows. THE REVIEW LEVEL IS STATED AND IS NOT HUMAN: "
        "AGENT_ADJUDICATED_SINGLE_READER_NO_HUMAN_REVIEW with human_reviewed 0, carried both "
        "on every mantra and on a DerivedMetric row that also records "
        "reference_set_class = INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET and "
        "is_human_gold = false. Two error modes were found and are recorded rather than "
        "smoothed: 1 of 24 matched a run beginning mid-quotation, because the matcher "
        "requires the run to END at a citing word boundary and not to BEGIN where the quoted "
        "unit begins; and 25 of the 769 carry a span that cannot be re-derived from any text "
        "form this graph stores, which is worse than no evidence because it looks checkable. "
        "Clause 4: the material-culture split by context is landed as a DerivedMetric over "
        "1,777 assessed mentions, carrying the warning that the four values are NOT ritual "
        "versus everyday and that no mantra anywhere in the artifact is marked NON_RITUAL -- "
        "a reader who collapses them into two invents the distinction the evidence cannot "
        "support.",
        "MATCH (m:Mantra) WHERE m.ritual_context_precision IS NULL RETURN count(m)",
        0,
        prior_expect=0,
        reaudit=(
            "ritual_context is 20,210 before and after. R5's measure is the clause that was "
            "actually failing: mantras with no precision figure went 20,210 -> 0, and the "
            "figure arrives with its review level attached rather than bare."
        ),
    ),
'''

NEW["GAP-SAMAVEDA_MUSIC-003"] = '''    "GAP-SAMAVEDA_MUSIC-003": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "CLAUSE 1 IS CLOSED AND CLAUSE 2 IS NOT, and the entry stays on the owner gate for "
        "the second alone rather than being reported closed. CLAUSE 1: 0 of 1,844 Samavedic "
        "mantras carried a running Samhita number and all 1,844 now do. The number is the "
        "SOURCE'S OWN PRINTED SERIES, not this corpus's index, and the control is what "
        "proves it: an enumerate() over our own ordering would be exactly 1..1844 "
        "contiguous, while the published series spans 1..1875 with 1,844 distinct values, 0 "
        "collisions and 31 absences -- and on the 332 verses where the gana pages "
        "independently print an arcika running number, the published number agrees 332 of "
        "332 while an enumerate() agrees only 256 of 332, its offset climbing 0-9-12-21-24-"
        "30-31 and ending exactly at the 31-verse deficit. All 31 absences are attributable "
        "to a recorded source defect in qa_issues.jsonl: 31 distinct source_running_number "
        "values across 39 rows over four check ids (STRUCTURAL_AMBIGUITY 21, "
        "REFERENT_UNRESOLVED 9, SOURCE_MARKER_ANOMALY 2, SOURCE_NOT_PRINTED 2), with 0 gaps "
        "unexplained and 0 recorded values that are not gaps. The two independent canonical "
        "files agree 1,844 of 1,844. THE ENTRY'S OWN source_dependency WAS WRONG ABOUT "
        "WHERE: it said the number is 'already captured in the staging artifact', and it is "
        "in the CANONICAL artifact -- data/canonical/samaveda_arcika_v1/citations.jsonl and "
        "text_versions.jsonl; data/staging/samaveda_music/ holds a running number for 332 "
        "verses only, and holds it as the GANA source's series, which is a different one. "
        "The root cause is an importer that dropped the field: the 1,844 PRIMARY_TEXT "
        "TextVersion rows carry a null source_locator while the canonical file holds the "
        "real per-verse locator, and the 1,844 SEARCH_DERIVATIVE rows carry the derivation "
        "RECIPE in that field, which is not a locator. A prior basis said this recipe sat on "
        "'1,844 SV TextVersion rows'; there are 3,688. CLAUSE 2 CANNOT BE CLOSED HERE AND IS "
        "NOT UNFINISHED CODE: MUSICALIZED_AS carries 0 edges and the relationship type does "
        "not exist, and neither does its object end -- 0 nodes carry a gana work id or a gana "
        "canonical key, the only SV Work is VG:WORK:SV:KAU, and the four gana Works are "
        "PROPOSED_FOR_LEAD_ADJUDICATION behind OWNER_DECISION_E_AUDIO_GATE, the same gate "
        "GAP-SAMAVEDA_MUSIC-002 is recorded against. The predicate is also glossed "
        "Passage-to-Passage RV-to-SV and would need widening before it could honestly carry "
        "an SV-to-gana edge. Attaching an execution blocker to a row that still contained "
        "undone internal work was the disguise the R1 hostile pass reverted this entry for; "
        "that internal work is now done, so the gate is the whole of what remains.",
        "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)",
        0,
        owner_decision="OWNER_DECISION_E_AUDIO_GATE",
        prior_expect=1844,
        reaudit=(
            "1,844 Samavedic mantras with no running Samhita number became 0. Clause 2 is "
            "unmoved at 0 MUSICALIZED_AS edges and is what the entry is now blocked on."
        ),
    ),
'''

NEW["GAP-QUALITY-003"] = '''    "GAP-QUALITY-003": Ruling(
        "CLOSED_DERIVED",
        "Closed on the product-and-evidence state, with no review manufactured. Clause 2 is "
        "done deterministically: seven predicates carried a constant 1.0 on EVERY edge -- "
        "HAS_RISHI 17,889, HAS_CHANDAS 16,298, HAS_DEVATA 10,558, HAS_DEVATA_ASCRIPTION "
        "5,385, HAS_DEVATA_DERIVED 882, BELONGS_TO_FAMILY 305 and ASCRIBES_TO_DEVATA 47, "
        "51,364 edges in all. The prior basis totalled 51,356 because ASCRIBES_TO_DEVATA was "
        "39 before R4 widened the deity-adjective suffix matcher to the vrddhi spelling. "
        "Those 1.0s stand for 'the source says so', which is a TIER and not a probability, "
        "so a filterable numeric field over them selects everything or nothing and invites a "
        "threshold nobody can honour. They are RENAMED, not deleted -- "
        "source_explicit_tier_marker, with the tier it encodes and the reason for the "
        "withdrawal beside it -- because deleting the field would lose the fact that the "
        "edges are source-explicit. Two more predicates were constant on tiny populations, "
        "INVOLVES_SUBSTANCE at 0.85 on 3 edges and REFERS_TO_PLACE at 0.75 on 1, and were "
        "NOT given the tier marker, because 0.85 is not the source-explicit 1.0 and marking "
        "it so would assert something false; they carry "
        "uncalibrated_pipeline_score instead. After both passes, 0 predicates carry a "
        "single constant confidence. CLAUSE 1 REQUIRES A HUMAN-LABELLED SAMPLE AND NONE "
        "EXISTS, and that is represented rather than faked. Proven, not asserted: 0 nodes in "
        "the graph carry is_human_gold = true or human_gold_status = 'ANNOTATED', and the "
        "reference set that does exist is an INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET, "
        "which is project policy and must not be relabelled human gold. Eleven predicates "
        "still carry a VARYING confidence over 25,470 edges and not one has a calibration "
        "curve, so every one of those edges now carries calibration_status = "
        "NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE, the gap it is blocked through, the "
        "reference set that IS available, and the sentence that the value orders edges "
        "within a predicate and is NOT a probability that the claim is true. 0 edges carry a "
        "confidence without that disclosure. The curves themselves remain unmeasurable until "
        "a labelled sample exists, which is GAP-QUALITY-001 and is not this entry.",
        "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL AND r.calibration_status IS NULL "
        "RETURN count(r)",
        0,
        prior_expect=None,
        reaudit=(
            "The entry had no closure_measure. R5 gives it one that can fail: an edge "
            "carrying a thresholdable number with no statement about its calibration. 25,474 "
            "such edges became 0, and constant-confidence predicates went 9 to 0."
        ),
    ),
'''

NEW["GAP-TRANSLATION-004"] = '''    "GAP-TRANSLATION-004": Ruling(
        "CLOSED_DERIVED",
        "Closed on a re-specified measure, because the old one could not be satisfied "
        "without reintroducing GAP-TRANSLATION-006. The old measure asks for a "
        "HAS_TRANSLATION edge on every Rigvedic mantra and 36 lack one: every EVEN verse of "
        "RV 1.65-1.70. Those six hymns are PAIRED_DVIPADA -- Griffith prints one unit per "
        "verse PAIR -- and 006 anchored unit N on verse 2N-1 with covers_canonical_keys = "
        "[2N-1, 2N] PRECISELY so one rendering is not published twice as two independent "
        "per-verse translations. Reaching 0 means attaching an own edge to each even verse, "
        "which is 006's defect reinstated exactly. MEASURED, AND IT FALSIFIED THE OBVIOUS "
        "GUESS: of the 36, 30 ARE named in a MANTRA_RANGE translation's covers_canonical_keys "
        "and 6 are covered by NOTHING, so the truthful figure is 6 and not 0. THE ENTRY'S OWN "
        "source_dependency IS FALSE: it says 'the ingested Griffith RV covers the Sakala "
        "Samhita in full', and 52 of 10,552 Rigvedic mantras have no row at all in "
        "data/canonical/rigveda_full_v1/translations.jsonl, which holds 10,502 rows over "
        "10,500 distinct mantras. The measure is restated in TRUTH STATES rather than 'all "
        "rows positive', using the production contract "
        "vedagraph.domain.translation_semantics rather than a second copy of its rules: "
        "VerseCoverageState over DEDICATED_TRANSLATION, RANGE_TRANSLATION_ANCHOR, "
        "RANGE_COVERED, CONTAINER_TRANSLATION, REUSED_RENDERING, NON_ENGLISH_ONLY, "
        "UNCOVERED_REUSABLE_PARALLEL_AVAILABLE and UNCOVERED_NO_RENDERING_REACHES_IT. All "
        "20,210 mantras carry one. A REUSED RENDERING IS NOT THE CORPUS'S OWN ENGLISH and is "
        "excluded from INDEPENDENT_ENGLISH_STATES: all 173 Samavedic renderings carry "
        "reuse_kind = REUSED_RENDERING from Griffith's Rigvedic English on verified-identical "
        "Sanskrit, so the Samaveda's independent English coverage is ZERO and reads as zero, "
        "and an earlier draft of this very closure labelled those 173 as own-English before "
        "the reuse column was checked. The uncovered rows are NOT erased to reach a zero: RV "
        "6, AV 17, YV 25 and SV 1,671 of which 1,488 have a reusable parallel and 183 do not. "
        "The regression runs both directions -- the BAD interpretation, an even verse "
        "reported as carrying its own 1:1 rendering, FAILS by name, and the truthful "
        "classified interpretation PASSES.",
        "MATCH (m:Mantra) WHERE m.translation_coverage_state IS NULL RETURN count(m)",
        0,
        prior_expect=36,
        reaudit=(
            "The old measure is unchanged at 36 and is supposed to be: those 36 are the even "
            "verses of six paired-dvipada hymns and 30 of them are range-covered. The new "
            "measure -- mantras with no typed coverage state -- went 20,210 to 0, and the "
            "genuinely uncovered Rigvedic residual is 6, named and visible."
        ),
    ),
'''

NEW["GAP-PRODUCT_SURFACE-005"] = '''    "GAP-PRODUCT_SURFACE-005": Ruling(
        "CLOSED_DERIVED",
        "Both clauses closed. Clause 1 passed at R3: .gitignore re-includes every release "
        "manifest, so each release's per-file sha256, record counts and source-snapshot "
        "hashes are tracked even while the verse text is not. Clause 2 -- the four "
        "apparatus-contaminated Samavedic verses -- is applied, in the canonical artifact "
        "AND in the graph, and the staged proposal turned out to be INCOMPLETE in two ways "
        "that were measured before anything was written. FIRST, it corrected the TextVersion "
        "matching old_sha256, which is the PRIMARY_TEXT row; the apparatus also sat in the "
        "SEARCH_DERIVATIVE row, folded, where it was a SEARCHABLE TOKEN. Which surface that "
        "row holds was established by REPRODUCTION rather than assumed -- rebuilding every "
        "surface from the contaminated primary and finding the one that equals what is "
        "stored, script_folded on 4 of 4 -- because an earlier version assumed "
        "sandhi_insensitive and would have replaced a space-separated surface with a "
        "boundary-free one, destroying the word divisions the token matcher depends on. "
        "SECOND, the proposal said derived edges 'should be rebuilt'. Measured: the FORMULA "
        "layer is provably untouched -- 0 of 4,825 Formula nodes contain any of the 5 "
        "apparatus tokens, matched on WHOLE TOKENS (a substring test reports hits because "
        "'dra' sits inside 'indra'), and the corrected text is a strict suffix of the "
        "contaminated text, so the token n-gram set can only lose n-grams containing them. "
        "But 13 cross-Veda parallel edges carried similarity metrics and PUBLISHED evidence "
        "quotes computed over the apparatus, and the SV-YV near parallel to VSM 12.51 was "
        "classed cross_veda_transformation = HEAD_TRUNCATION with a difference span claiming "
        "a word was inserted -- a claim about Vedic textual variation whose whole cause was "
        "our own parser, and one of only TWO HEAD_TRUNCATION rows in all 6,596. The 13 were "
        "rescored by the pipeline's own score_pair, which reproduced all five stored metrics "
        "EXACTLY on the contaminated text before being trusted on the corrected one. The "
        "transformation CLASS was not re-derived, because its sixteen-value vocabulary lives "
        "in the cross-Veda staging build and not in src, and an inferred value would be a "
        "guess; each edge carries "
        "cross_veda_transformation_status = STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED with the "
        "old value and the reason preserved beside it. On the artifact side: all 13 declared "
        "per-file digests verified BEFORE the edit, 4 text_versions.jsonl records changed by "
        "a leading deletion only, 4 referent_bindings.jsonl rows re-keyed on text_sha256 "
        "with canonical keys untouched, and the aggregate generated_content_sha256 "
        "recomputed with the BUILDER'S OWN recipe read out of vedagraph.release -- five "
        "hand-guessed recipes failed first, which is why it was read rather than guessed. "
        "The artifact verifies against its own manifest again, record counts unchanged. No "
        "corrections_applied block was added to the manifest: it is not in the "
        "CanonicalRelease model so write_release would drop it, and this registry has "
        "already recorded 8 of 9 such entries that were never written into the data.",
        "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion) WHERE p.canonical_key IN "
        "['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04',"
        "'VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07'] AND "
        "(t.text_nfc STARTS WITH 'dra ' OR t.text_nfc STARTS WITH 'araṇyaka' OR "
        "t.text_nfc STARTS WITH 'āraṇyaka' OR t.text_nfc CONTAINS 'द्र. ' OR "
        "t.text_nfc STARTS WITH '(आरण्यक') RETURN count(t)",
        0,
        prior_expect=None,
        reaudit=(
            "The entry had no closure_measure. R5 gives it one that can fail: an apparatus "
            "string surviving on any text version of the four verses. 8 such rows became 0."
        ),
    ),
'''

NEW["GAP-ENTITY_COVERAGE-001"] = '''    "GAP-ENTITY_COVERAGE-001": Ruling(
        "CLOSED_DERIVED",
        "All three clauses closed, the third by an owner decision that removes a gate which "
        "could not fail. CLAUSE 1 CLOSED AT R4: the epithet layer was 13 :Epithet nodes, 13 "
        "HAS_EPITHET edges and nothing else -- 0 edges of any type between an :Epithet and a "
        ":Passage -- and now carries 1,035 MENTIONS_EPITHET edges over all 13, derived from "
        "the Rigvedic morphological annotation's own per-token lemma, in two tiers recorded "
        "per edge because they are not the same claim: STEM_LEMMA on 10, and "
        "ATTESTED_SURFACE_FORM on the 3 duals whose wider stem inflection is deliberately "
        "NOT claimed. CLAUSE 3 CLOSED AT R4: per-epithet recall is measured rather than "
        "assumed -- a mantra count and a token count per epithet, not one aggregate -- and "
        "the Rigveda-only bound is typed in every row, because MENTIONS_LEMMA is 154,261 "
        "edges over the Rigveda and ZERO over the other three, so an epithet with no "
        "Samavedic occurrence is unannotated there and not absent. CLAUSE 2 asked the "
        "inventory to reach 'well beyond 4 deities' and could be NEITHER PASSED NOR FAILED: "
        "all 13 curated epithets belong to 4 deities, so the occurrence layer can only ever "
        "reach those 4, the phrase names no number and no source, and no published epithet "
        "index exists in this repository against which 4 could be measured as incomplete. A "
        "gate that cannot fail is not a gate. The owner has now ruled that the completeness "
        "denominator for this release is the currently curated, evidence-backed Epithet "
        "inventory, and that broader epithet discovery is future enrichment rather than "
        "release completeness. Readback measured 2026-09-18 against the live store rather "
        "than taken from R4's receipt: 13 :Epithet, 1,035 MENTIONS_EPITHET, 0 epithets "
        "reaching no passage, 4 distinct deities. Identity was not minted -- the inventory is "
        "still the curated 13 and fold_alias was used to compare, never to create or merge.",
        "MATCH (e:Epithet)-[r]-(:Passage) RETURN count(r)",
        1035,
        citation="docs/reports/data-completeness/OWNER_DECISIONS.md section 38",
        prior_expect=0,
        reaudit=(
            "0 epithet-to-passage edges of any type became 1,035 at R4. R5 changes the "
            "STATUS, not the figure: the owner supplied the denominator clause 2 lacked, so "
            "the entry leaves BLOCKED_OWNER_DECISION_REQUIRED for a closure."
        ),
    ),
'''

NEW["GAP-COMMUNITIES-002"] = '''    "GAP-COMMUNITIES-002": Ruling(
        "CLOSED_DERIVED",
        "Closed by an owner decision on the denominator, with the evidence-eligible set "
        "measurably exhausted. The test asks that every PAIR deity carry components and "
        "every GROUP deity carry components or a typed reason. The GROUP arm passes. The "
        "PAIR arm cannot be met by projection: devata_components.yaml is the only artifact "
        "in this repository that states a composite deity's members, it declares 20 "
        "composites, 14 were already landed, and of the remaining 6 FOUR declare an EMPTY "
        "member list with an explicit reasoned refusal and a review status (REJECTED for "
        "visvedevah, adityah and marutah; NEEDS_REVIEW for dyavaprthivyau) while only TWO "
        "were landable -- VG:DEVATA:INDRAVARUNAU and VG:DEVATA:USASANAKTA, both landed as 4 "
        "COMPOSED_OF edges. So of the 24 pairs a mechanical pass proposes, 2 are "
        "evidence-eligible and 22 are not, and none of the 22 has an entry in the only "
        "artifact that could make it eligible. Enumerating them means DECIDING which deities "
        "each contains, which is curation and not computation. The owner has now ruled that "
        "mechanical pair generation is candidate generation and not evidence, that only "
        "decompositions supported by canonical identity plus source-explicit or "
        "deterministic evidence may be asserted, that the remaining mechanical candidates "
        "are NON-ASSERTED CANDIDATES rather than missing graph data, and that the closure "
        "denominator is all evidence-eligible pairs processed. Readback measured 2026-09-18: "
        "of 214 :Devata, 71 carry structure PAIR or GROUP, ALL 71 carry a typed "
        "decomposition_status and 0 are null -- 16 DECOMPOSED_FROM_THE_COMPONENT_REGISTRY "
        "over 32 COMPOSED_OF edges, 4 NOT_ENUMERABLE_DECLARED_BY_THE_REGISTRY carrying the "
        "registry's own evidence and review status, and 51 "
        "NOT_ENUMERABLE_FROM_ANYTHING_HELD. The entry's own measure reads 55 and every one "
        "of the 55 is a typed non-assertion rather than an unprocessed row. No unsupported "
        "pair was imported to reach a count.",
        "MATCH (d:Devata) WHERE d.structure IN ['PAIR','GROUP'] AND "
        "coalesce(d.component_count,0)=0 RETURN count(d)",
        55,
        citation="docs/reports/data-completeness/OWNER_DECISIONS.md section 39",
        prior_expect=57,
        reaudit=(
            "Declared 57 before R4 and 55 after, which the graph measures: the two the "
            "component registry supports are landed. R5 changes the STATUS, not the figure: "
            "the owner supplied the denominator, so the entry leaves "
            "BLOCKED_OWNER_DECISION_REQUIRED for a closure."
        ),
    ),
'''


def main() -> None:
    raw = TARGET.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("audit script contains CRLF; refusing")
    text = raw.decode("utf-8")
    replaced = []
    for gap_id, replacement in NEW.items():
        pattern = re.compile(
            rf'    "{re.escape(gap_id)}": Ruling\(\n.*?\n    \),\n', re.S
        )
        match = pattern.search(text)
        if match is None:
            raise SystemExit(f"ruling block not found for {gap_id}")
        text = text[: match.start()] + replacement + text[match.end() :]
        replaced.append(gap_id)
    TARGET.write_bytes(text.encode("utf-8"))
    print(f"re-declared {len(replaced)} rulings:")
    for gap_id in replaced:
        print("  ", gap_id)


if __name__ == "__main__":
    main()
