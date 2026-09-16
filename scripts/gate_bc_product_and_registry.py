#!/usr/bin/env python3
"""Phases 11-12: can the product tell the truth about this data, and what does the registry owe?

Phase 11 is a precondition, not a formality. The campaign's rule is that a population which
would require a semantic distinction the product cannot express is BLOCKED_PRODUCT_SEMANTICS
and is not imported first and represented later. So each candidate class is checked against
three surfaces in turn -- the graph's own vocabulary, the API model that projects it, and the
frontend component that renders it -- because a distinction can exist in the data model and
still be invisible to every reader, which is the same as not existing for the person the
product is for.

Phase 12 proposes registry status changes and refuses to propose closures. A gap is not
closed by the existence of staging; Wave 4's finding was precisely a registry that recorded
"closed via the Wayback Machine, 944 of 961" against a graph holding none of them.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

from gate_bc_common import PACKET, REPO, write_json


def jl(name):
    return [
        json.loads(line)
        for line in (PACKET / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    matrix = json.loads((PACKET / "translation_decision_matrix.json").read_text(encoding="utf-8"))
    by_class = {c["final_class"]: c for c in matrix["classes"]}
    per_row = matrix["per_row"]
    gc = {r["staged_row_id"]: r for r in jl("gate_c_rows.jsonl")}

    # ---------------------------------------------------------------------------------
    # PHASE 11 -- product semantics
    # ---------------------------------------------------------------------------------
    enums = (REPO / "src" / "vedagraph" / "models" / "enums.py").read_text(encoding="utf-8")
    api_passage = (REPO / "src" / "vedagraph" / "api" / "models" / "passage.py").read_text(
        encoding="utf-8"
    )
    svc = (REPO / "src" / "vedagraph" / "api" / "services" / "passage_service.py").read_text(
        encoding="utf-8"
    )
    reader = (REPO / "frontend" / "src" / "app" / "passage" / "[key]" / "page.tsx").read_text(
        encoding="utf-8"
    )
    fe_schema = (REPO / "frontend" / "src" / "lib" / "api-schema.ts").read_text(encoding="utf-8")

    surfaces = {
        "graph_vocabulary": {
            "alignment_level_enum_has_MANTRA": "MANTRA = " in enums,
            "alignment_level_enum_has_MANTRA_RANGE": 'MANTRA_RANGE = "MANTRA_RANGE"' in enums,
            "translation_node_carries_alignment_level": "alignment_level" in svc,
            "translation_node_carries_language": "language" in api_passage,
            "translation_node_can_name_the_verse_a_rendering_was_borrowed_from": False,
            "note": (
                "MANTRA and MANTRA_RANGE are both first-class members of AlignmentLevel, and "
                "MANTRA_RANGE was added by GAP-TRANSLATION-006 for exactly this shape. There "
                "is no property anywhere on :Translation that records the passage a reused "
                "rendering was taken from: the graph has REUSES_TEXT_FROM and VARIANT_OF "
                "edges between the two mantras, but nothing ties the Translation node to the "
                "verse whose rendering it is."
            ),
        },
        "passage_api": {
            "translation_view_exposes_alignment_level": "alignment_level: str | None" in api_passage,
            "translation_view_exposes_language": "language: str" in api_passage,
            "translation_view_exposes_quality_status": "quality_status" in api_passage,
            "translation_view_exposes_work_edition": "work_edition" in api_passage,
            "service_selects_alignment_level": "alignment_level: t.alignment_level" in svc,
            "translation_view_exposes_a_reuse_disclosure_field": False,
            "note": (
                "TranslationView carries alignment_level, language, quality_status and "
                "work_edition, and the service projects them, so MANTRA vs MANTRA_RANGE is "
                "fully expressible over the API today. A reused rendering has no field: the "
                "only signal would be work_edition reading 'The Hymns of the Rigveda' on a "
                "Samavedic verse, which is accurate and unexplained."
            ),
        },
        "coverage_statistics": {
            "percent_is_computed_not_transcribed": "round(100 * translated / mantras" in svc,
            "counts_verses_carrying_an_edge": True,
            "separates_dedicated_from_range_covered": False,
            "separates_reused_renderings": False,
            "carries_a_machine_aligned_caveat": "MACHINE_ALIGNED" in svc,
            "note": (
                "TranslationCoverage counts mantras carrying a HAS_TRANSLATION edge and "
                "divides. It cannot currently distinguish a verse with its own rendering from "
                "one sharing a neighbour's span or showing another corpus's rendering, so an "
                "import of the reuse or range classes would move a single percentage that "
                "three different kinds of coverage feed into."
            ),
        },
        "frontend_reader": {
            "renders_translation_text": "blockquote>{translation.text}" in reader,
            "renders_translator_and_year": "translation.translator" in reader,
            "renders_work_edition": "translation.work_edition" in reader,
            "renders_alignment_level": "alignment_level" in reader,
            "renders_language": re.search(r"translation\.language", reader) is not None,
            "alignment_level_present_in_generated_client_types": "alignment_level?: string | null"
            in fe_schema,
            "empty_state_copy": (
                "No released translation covers this passage in the current build. The verse "
                "is held; its translation layer is not."
            ),
            "note": (
                "the reader shows text, translator, year and edition. It does not read "
                "alignment_level, although the generated client types carry it, so a "
                "MANTRA_RANGE rendering is displayed exactly like a dedicated one. And its "
                "empty state asserts that no translation covers the passage, which is "
                "already false for the 30 even verses of RV 1.65-1.70: a MANTRA_RANGE on the "
                "paired odd verse does cover them. That defect is a consequence of M13 "
                "landing correctly in the data and is live now, independent of any import."
            ),
        },
        "ask_evidence": {
            "retriever_selects_translation_text": True,
            "retriever_selects_alignment_level": False,
            "note": (
                "src/vedagraph/api/ask/retriever.py matches HAS_TRANSLATION and reads the "
                "text for evidence. It does not read alignment_level, so an answer quoting a "
                "reused Rigvedic rendering as evidence about a Samavedic verse would cite it "
                "as that verse's translation, and a quote drawn from a MANTRA_RANGE would be "
                "attributed to one verse of the span."
            ),
        },
    }

    verdicts = {
        "MANTRA": {
            "representable_in_graph": True,
            "representable_in_api": True,
            "rendered_truthfully_in_frontend": True,
            "verdict": "REPRESENTABLE",
            "blocking": False,
        },
        "MANTRA_RANGE": {
            "representable_in_graph": True,
            "representable_in_api": True,
            "rendered_truthfully_in_frontend": False,
            "verdict": "REPRESENTABLE_IN_DATA_NOT_YET_IN_PRODUCT",
            "blocking": True,
            "what_is_missing": [
                "the reader does not display alignment_level, so a rendering covering two "
                "verses is shown as if it were this verse's own",
                "the reader's empty state says no translation covers a passage that a "
                "sibling's MANTRA_RANGE does cover",
                "TranslationCoverage cannot separate dedicated from range-covered verses",
            ],
            "already_live_defect": True,
            "note": (
                "this is not introduced by the candidate import. M13 has already put 30 "
                "MANTRA_RANGE translations into the Rigveda, so the gap between the typed "
                "data and the rendered product exists today."
            ),
        },
        "REUSED_CROSS_CORPUS_RENDERING": {
            "representable_in_graph": False,
            "representable_in_api": False,
            "rendered_truthfully_in_frontend": False,
            "verdict": "NOT_REPRESENTABLE",
            "blocking": True,
            "what_is_missing": [
                "no property on :Translation names the passage whose rendering this is",
                "TranslationView has no disclosure field, so a client cannot tell",
                "the reader would present Griffith's Rigveda English as the Samavedic or "
                "Atharvavedic verse's translation, with 'The Hymns of the Rigveda' in the "
                "edition line as the only clue",
                "Ask would cite it as evidence about the target corpus",
            ],
            "already_live_defect": False,
        },
        "LATIN_SUBSTITUTION": {
            "representable_in_graph": True,
            "representable_in_api": True,
            "rendered_truthfully_in_frontend": False,
            "verdict": "REPRESENTABLE_ONLY_AFTER_THE_LANGUAGE_FIELD_IS_CORRECTED",
            "blocking": True,
            "what_is_missing": [
                "the 22 rows declare language 'en' and the literal is Latin, so the field "
                "would have to be corrected before import, not after",
                "the reader displays no language marker, so a Latin rendering appears under "
                "the heading 'Translation' with no indication",
            ],
            "already_live_defect": False,
        },
    }

    blocked = {
        "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE": "REUSED_CROSS_CORPUS_RENDERING",
        "SAFE_IMPORT_MULTI_VERSE_RANGE": "MANTRA_RANGE",
    }
    approvable_now, blocked_now = {}, {}
    for cls, c in by_class.items():
        if not c["eligible_for_an_import_plan"]:
            continue
        if cls in blocked:
            blocked_now[cls] = {
                "count": c["count"],
                "by_veda": c["by_veda"],
                "blocked_on": blocked[cls],
                "verdict": verdicts[blocked[cls]]["verdict"],
            }
        else:
            approvable_now[cls] = {"count": c["count"], "by_veda": c["by_veda"]}

    write_json(
        "product_semantics_check.json",
        {
            "phase": 11,
            "rule_applied": (
                "a population requiring a semantic distinction the product cannot express is "
                "marked BLOCKED_PRODUCT_SEMANTICS and is not imported ahead of the "
                "representation"
            ),
            "surfaces_checked": surfaces,
            "distinction_verdicts": verdicts,
            "evidence_paths": {
                "alignment_level_enum": "src/vedagraph/models/enums.py::AlignmentLevel",
                "api_model": "src/vedagraph/api/models/passage.py::TranslationView",
                "api_projection": "src/vedagraph/api/services/passage_service.py",
                "coverage_model": "src/vedagraph/api/models/work.py::TranslationCoverage",
                "frontend_reader": "frontend/src/app/passage/[key]/page.tsx",
                "frontend_types": "frontend/src/lib/api-schema.ts",
                "ask_retriever": "src/vedagraph/api/ask/retriever.py",
            },
            "import_plan_split_by_product_readiness": {
                "approvable_on_evidence_and_representable_now": approvable_now,
                "approvable_on_evidence_but_BLOCKED_PRODUCT_SEMANTICS": blocked_now,
                "totals": {
                    "evidence_safe": sum(
                        c["count"] for c in by_class.values() if c["eligible_for_an_import_plan"]
                    ),
                    "representable_now": sum(v["count"] for v in approvable_now.values()),
                    "blocked_on_product_semantics": sum(
                        v["count"] for v in blocked_now.values()
                    ),
                },
            },
            "pre_existing_product_defect_found_by_this_review": {
                "what": (
                    "the passage reader tells a visitor that no translation covers RV 1.65.2, "
                    "1.65.4, 1.65.6, 1.65.8, 1.65.10 and the 25 other even verses of "
                    "RV 1.65-1.70, while a MANTRA_RANGE translation on the paired odd verse "
                    "does cover them"
                ),
                "population": 30,
                "introduced_by": "GAP-TRANSLATION-006 / M13, which typed the data correctly",
                "caused_by_this_task": False,
                "in_scope_of_this_task": False,
                "recommended_owner_action": (
                    "fix the reader and TranslationCoverage before importing any further "
                    "MANTRA_RANGE population, because the same 68 Atharvavedic rows would "
                    "extend a defect that is currently 30 verses wide"
                ),
            },
        },
    )

    # ---------------------------------------------------------------------------------
    # PHASE 12 -- registry consequences
    # ---------------------------------------------------------------------------------
    reg = json.loads((REPO / "data" / "gap_registry.json").read_text(encoding="utf-8"))
    gaps = {g["gap_id"]: g for g in reg["gaps"]}

    def cls_count(name, veda=None):
        return sum(
            1
            for r in per_row
            if r["final_class"] == name and (veda is None or r["veda"] == veda)
        )

    def safe_for(veda):
        return sum(
            1
            for r in per_row
            if r["veda"] == veda
            and by_class.get(r["final_class"], {}).get("eligible_for_an_import_plan")
        )

    consequences = [
        {
            "gap_id": "GAP-TRANSLATION-001",
            "domain": "translation",
            "current_status": gaps["GAP-TRANSLATION-001"]["status"],
            "current_closure_owner_decision": gaps["GAP-TRANSLATION-001"].get(
                "closure_owner_decision"
            ),
            "measured_truth": (
                "the Samaveda still holds 0 of 1,844 translations. Of the 1,242 staged "
                f"Samavedic rows, {safe_for('SV')} survive both gates and every one of them "
                "is a reused Rigvedic rendering, not a Samavedic translation: 735 are "
                "PROBABLE and withheld by the central policy, 285 have a printed locator "
                "that addresses up to 22 canonical keys, and 49 cite an archive capture with "
                "no content hash. Griffith's Samaveda is the RANAYANIYA recension and this "
                "corpus is KAUTHUMA, which the staging agent's own residual proof states."
            ),
            "proposed_post_owner_decision_status": "STILL_IMPLEMENTATION_FIXABLE",
            "must_not_become": "CLOSED",
            "why": (
                "even if every safe row were imported the Samaveda would hold 173 of 1,844, "
                "and all 173 would be another corpus's English. No Kauthuma translation has "
                "been found; the closure_test as written ('every SV Translation node carries "
                "a Kauthuma-aligned source_id') would be false for all 173."
            ),
            "closure_evidence_required": (
                "a Kauthuma witness. The staging agent names Benfey 1848 as the highest-"
                "leverage artifact, which carries Griffith's own base Sanskrit and would "
                "convert the 735 PROBABLE rows into decidable ones."
            ),
            "owner_decision_dependency_should_change_to": (
                "OWNER_DECISION_D_REUSED_RENDERING_POLICY -- the Samavedic question is not "
                "about the RV span or forced addresses at all, and is mis-gated today"
            ),
        },
        {
            "gap_id": "GAP-TRANSLATION-002",
            "domain": "translation",
            "current_status": gaps["GAP-TRANSLATION-002"]["status"],
            "current_closure_owner_decision": gaps["GAP-TRANSLATION-002"].get(
                "closure_owner_decision"
            ),
            "measured_truth": (
                "AV coverage is 4,878 of 5,839, still the pre-closure figure. Of 944 staged "
                f"Atharvavedic rows, {safe_for('AV')} survive both gates: "
                f"{cls_count('SAFE_IMPORT_SOURCE_EXPLICIT', 'AV')} source-explicit, "
                f"{cls_count('SAFE_IMPORT_MULTI_VERSE_RANGE', 'AV')} multi-verse ranges and "
                f"{cls_count('SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE', 'AV')} reused "
                "Rigvedic renderings. 17 are withheld because the literal is Griffith's "
                "Latin. The archive evidence is the strongest in the artifact: 923 of 923 "
                "rows name a page hash and every one is present in the artifact's own page "
                "proofs, 147 pages all HTTP 200."
            ),
            "proposed_post_owner_decision_status": "STILL_IMPLEMENTATION_FIXABLE",
            "must_not_become": "CLOSED",
            "why": (
                "an approved import would take AV to 5,805 of 5,839, not to 5,839. 34 verses "
                "would remain uncovered and the closure_test requires zero. 68 of the 927 "
                "would be range-covered and 21 would show Rigvedic English."
            ),
            "closure_evidence_required": (
                "the import executed and read back, plus a disposition for the 17 Latin rows "
                "and the 34 residual verses"
            ),
        },
        {
            "gap_id": "GAP-TRANSLATION-003",
            "domain": "translation",
            "current_status": gaps["GAP-TRANSLATION-003"]["status"],
            "current_closure_owner_decision": gaps["GAP-TRANSLATION-003"].get(
                "closure_owner_decision"
            ),
            "measured_truth": (
                "YV coverage is 1,903 of 1,975. Of 51 staged rows, "
                f"{safe_for('YV')} survive both gates and are independently verified against "
                "the pinned Griffith snapshot's own printed labels. 12 are withheld: 11 for "
                "naming no content hash for the bytes they were read from, 1 PROBABLE, and 1 "
                "rejected because the literal is an editorial cross-reference. The registry's "
                "root cause -- 39 of 72 gap labels being digit-confusion OCR with the text "
                "present throughout -- is confirmed: the source prints a correct label for 18 "
                "of the 39 and brackets the slot uniquely for 19 more."
            ),
            "proposed_post_owner_decision_status": "STILL_IMPLEMENTATION_FIXABLE",
            "must_not_become": "CLOSED",
            "why": "an approved import reaches 1,939 of 1,975; the closure_test requires zero remaining",
            "closure_evidence_required": (
                "the import executed and read back, plus a content hash for the 11 adhyaya-12 "
                "rows so their bytes are pinned like the other 39"
            ),
        },
        {
            "gap_id": "GAP-TRANSLATION-004",
            "domain": "translation",
            "current_status": gaps["GAP-TRANSLATION-004"]["status"],
            "current_closure_owner_decision": gaps["GAP-TRANSLATION-004"].get(
                "closure_owner_decision"
            ),
            "measured_truth": (
                "50 Rigvedic verses carry no translation edge. 30 are the even verses of "
                "RV 1.65-1.70 and every one is covered by a MANTRA_RANGE on its paired odd "
                "verse -- they lack a dedicated 1:1 rendering because Griffith printed none, "
                "which is not the same thing as a missing translation. Of the other 20, 17 "
                "are staged (8 safe, 5 Latin, 4 PROBABLE) and 3 have no candidate source at "
                "all: RV 8.93.29, 10.86.16 and 10.86.17."
            ),
            "proposed_post_owner_decision_status": "STILL_IMPLEMENTATION_FIXABLE",
            "must_not_become": "CLOSED",
            "why": (
                "the coordinate defect this gap records IS repaired, and that part is "
                "mechanically determined. But the gap's own closure_test counts verses with "
                "no HAS_TRANSLATION edge and would still return 42."
            ),
            "closure_evidence_required": (
                "either a source for the 3 unstaged verses and a Latin disposition, or a "
                "closure_measure rewritten to count covered verses rather than edges -- the "
                "present measure cannot express a range-covered verse and will never reach "
                "zero while Griffith's merged units are represented truthfully"
            ),
            "recommended_measure_change": (
                "the current closure_measure counts DISTINCT m with an edge. A verse covered "
                "by a sibling's MANTRA_RANGE is a covered verse with no edge, so the measure "
                "understates coverage by exactly the 30 verses M13 fixed. This is the "
                "registry equivalent of the reader's empty-state defect."
            ),
        },
        {
            "gap_id": "OWNER_DECISION_A_RV_SPAN",
            "domain": "owner_decision",
            "current_status": "OPEN (referenced by GAP-TRANSLATION-001/002/003/004)",
            "measured_truth": (
                "the hazard it protects against -- Griffith's merged dvipada unit bound 1:1 "
                "to a canonical verse -- is gone. 30 of 30 span verses are covered by a "
                "MANTRA_RANGE, the M13 readback is clean with 0 findings, and no staged row "
                "targets the span."
            ),
            "proposed_post_owner_decision_status": "CLOSED_DERIVED on the span; the residual "
            "is not an RV-span question and should be re-filed",
            "mechanically_determined": True,
            "needs_owner_judgement": False,
            "why": (
                "nothing about the paired spine remains for an owner to approve or refuse. "
                "Leaving the decision open over RV 1.179's Latin and three source-less verses "
                "would make the owner re-decide a resolved coordinate question to reach an "
                "unrelated editorial one."
            ),
            "action_not_taken_here": (
                "the status is proposed, not written. The instruction is not to mutate final "
                "owner-decision statuses, and although the span part is mechanically "
                "determined, retiring the decision also unblocks three other gaps that cite "
                "it, which is a scope change the owner should see first."
            ),
            "should_no_longer_gate": [
                "GAP-TRANSLATION-001",
                "GAP-TRANSLATION-002",
                "GAP-TRANSLATION-003",
            ],
            "why_it_should_not_gate_them": (
                "none of the Samavedic, Atharvavedic or Yajurvedic populations involves the "
                "Rigvedic paired dvipada spine. They were gated on it because the decision "
                "was written over a mixed population."
            ),
        },
        {
            "gap_id": "OWNER_DECISION_C_FORCED_ADDRESSES",
            "domain": "owner_decision",
            "current_status": "OPEN (referenced by GAP-TRANSLATION-001/002/003)",
            "measured_truth": (
                "39 rows carry the label-defect flag, 31 of them declaring no content "
                "control. Independent verification against the pinned snapshot finds the "
                "declaration wrong for most: the source prints a correct legible label for 18 "
                "of the 39 and brackets the canonical slot uniquely with its own printed "
                "neighbours for 19 more. 2 remain unverified and 1 is rejected on its literal."
            ),
            "proposed_post_owner_decision_status": "NARROWED to 3 rows",
            "mechanically_determined": False,
            "needs_owner_judgement": True,
            "why": (
                "36 rows now have an independent source-local control of the kind the "
                "decision asks for, so the decision's population is 3, not 31. The remaining "
                "judgement is whether a printed neighbour bracket counts as independent "
                "content control, which is the owner's call and is why this is not written as "
                "decided."
            ),
            "should_no_longer_gate": ["GAP-TRANSLATION-001", "GAP-TRANSLATION-002"],
            "why_it_should_not_gate_them": (
                "every forced address in the artifact is Yajurvedic. Gating the Samavedic and "
                "Atharvavedic gaps on it blocks 1,242 and 944 rows on a question about 39 "
                "Yajurvedic ones."
            ),
        },
        {
            "gap_id": "GAP-FORMULA-003",
            "domain": "enrich",
            "current_status": "pre-existing failing test, out of scope",
            "measured_truth": (
                "tests/enrich/test_formula_families.py pins 1,103 nested formulas and measures "
                "1,064. Baselined at phase 0 and re-measured at phase 14 of this task."
            ),
            "proposed_post_owner_decision_status": "unchanged",
            "why": "explicitly out of scope; recorded only to prove this task did not move it",
        },
    ]

    new_decisions = [
        {
            "proposed_id": "OWNER_DECISION_D_REUSED_RENDERING_POLICY",
            "population": by_class.get(
                "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE", {}
            ).get("count", 0),
            "by_veda": by_class.get("SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE", {}).get(
                "by_veda", {}
            ),
            "question": (
                "may Griffith's Rigveda rendering be published as the English for a Samavedic "
                "or Atharvavedic verse whose Sanskrit is verified character-identical, given "
                "that it is disclosed as a reused rendering and is never counted as "
                "independent semantic evidence for the target corpus?"
            ),
            "why_it_is_a_new_decision": (
                "it is currently buried inside OWNER_DECISION_A_RV_SPAN and "
                "OWNER_DECISION_C_FORCED_ADDRESSES, neither of which is about cross-corpus "
                "reuse. It is the single largest question in the artifact by row count and it "
                "is genuinely editorial, not mechanical."
            ),
            "blocked_on_product_semantics": True,
        },
        {
            "proposed_id": "OWNER_DECISION_F_LATIN_SUBSTITUTION",
            "population": 22,
            "by_veda": dict(
                Counter(
                    r["veda"]
                    for r in per_row
                    if gc[r["staged_row_id"]]["evidence"]["literal_integrity"]["detected"][
                        "verdict"
                    ]
                    in {"LATIN", "NOT_RECOGNISABLY_ENGLISH"}
                )
            ),
            "question": (
                "Griffith renders sexually explicit passages into Latin. The text is his and "
                "is public domain. Publish it with language corrected to 'la' and a "
                "disclosure, leave the verses uncovered, or commission an English rendering?"
            ),
            "why_it_is_a_new_decision": (
                "it was not visible as a population before this pass: all 22 rows declare "
                "language 'en' and pass every structural check"
            ),
            "blocked_on_product_semantics": True,
        },
    ]

    write_json(
        "registry_consequences.json",
        {
            "phase": 12,
            "rule_applied": (
                "no gap is proposed for closure on the strength of staging. A closure needs "
                "the measure to have moved in the graph, which no row in this packet has done."
            ),
            "gaps_affected": len(consequences),
            "closures_proposed": 0,
            "statuses_mutated_by_this_task": 0,
            "consequences": consequences,
            "decisions_recommended_for_decomposition": new_decisions,
            "summary": {
                "could_close_after_an_approved_and_executed_import": [],
                "must_remain_open": [
                    "GAP-TRANSLATION-001",
                    "GAP-TRANSLATION-002",
                    "GAP-TRANSLATION-003",
                    "GAP-TRANSLATION-004",
                ],
                "mechanically_resolvable_without_owner_judgement": [
                    "OWNER_DECISION_A_RV_SPAN (span part only)"
                ],
                "narrowable": ["OWNER_DECISION_C_FORCED_ADDRESSES (31 -> 3)"],
            },
        },
    )

    print("=== PHASE 11 PRODUCT SEMANTICS ===")
    for k, v in verdicts.items():
        print(f"  {k}: {v['verdict']}  blocking={v['blocking']}")
    print(f"  evidence-safe rows: {sum(c['count'] for c in by_class.values() if c['eligible_for_an_import_plan'])}")
    print(f"  representable now : {sum(v['count'] for v in approvable_now.values())} {approvable_now}")
    print(f"  BLOCKED_PRODUCT_SEMANTICS: {sum(v['count'] for v in blocked_now.values())} "
          f"{ {k: v['count'] for k, v in blocked_now.items()} }")
    print("=== PHASE 12 REGISTRY ===")
    for c in consequences:
        print(f"  {c['gap_id']}: {c['current_status']} -> {c['proposed_post_owner_decision_status']}")
    print(f"  closures proposed: 0   statuses mutated: 0")
    for d in new_decisions:
        print(f"  NEW: {d['proposed_id']} over {d['population']} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
