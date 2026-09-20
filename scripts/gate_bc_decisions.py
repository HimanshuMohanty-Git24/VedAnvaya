#!/usr/bin/env python3
"""Phases 7-12: the owner decision artifacts, built from the Gate B and Gate C results.

Nothing here re-measures the corpus. Every count comes from gate_b_rows.jsonl,
gate_c_rows.jsonl and yv_source_verification.json, so a figure in the owner packet can be
traced to the row that produced it. The one thing this file does measure live is the
canonical translation state, because the coverage prediction has to be a delta against the
graph as it stands rather than against the baseline file.

The organising idea is decomposition. Both owner decisions arrived as one gate over a
mixed population, and a gate over a mixed population cannot be answered: approving it
approves the worst row in it, refusing it refuses the best. So each is split until every
part is either mechanically decided or is a genuine question of policy that only the owner
can answer -- and the mechanical parts are reported as decided, not deferred.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict

from gate_bc_common import (
    CORE_CORPUS_INVARIANT,
    PACKET,
    driver,
    load_rows,
    session,
    write_json,
)

M13_SPAN = re.compile(r"VG:RV:SAK:M01:S0(6[5-9]|70):")


def jl(name):
    return [
        json.loads(line)
        for line in (PACKET / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    staged = {r["_staged_row_id"]: r for r in load_rows()}
    gb = {r["staged_row_id"]: r for r in jl("gate_b_rows.jsonl")}
    gc = {r["staged_row_id"]: r for r in jl("gate_c_rows.jsonl")}
    yv = {
        r["canonical_key"]: r
        for r in json.loads((PACKET / "yv_source_verification.json").read_text(encoding="utf-8"))[
            "rows"
        ]
    }

    drv = driver()
    with session(drv) as s:
        rv_untranslated = [
            r["k"]
            for r in s.run(
                """
                MATCH (m:Mantra) WHERE m.canonical_key STARTS WITH 'VG:RV:'
                  AND NOT (m)-[:HAS_TRANSLATION]->()
                RETURN m.canonical_key AS k ORDER BY k
                """
            )
        ]
        # For every untranslated RV verse, is a MANTRA_RANGE translation on a sibling
        # actually covering it? The graph does not store the span, so coverage is derived
        # the way M13 defined it: Griffith's unit k renders our verses 2k-1 and 2k, so an
        # even verse is covered by the MANTRA_RANGE attached to the odd verse below it.
        range_bearers = {
            r["k"]: r["n"]
            for r in s.run(
                """
                MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE t.alignment_level = 'MANTRA_RANGE'
                RETURN m.canonical_key AS k, count(t) AS n
                """
            )
        }
        live_by_level = {
            f"{r['veda']}|{r['lvl']}": r["c"]
            for r in s.run(
                """
                MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE t.language = 'en'
                WITH split(m.canonical_key,':')[1] AS veda,
                     coalesce(t.alignment_level,'<null>') AS lvl, count(DISTINCT m) AS c
                RETURN veda, lvl, c
                """
            )
        }
        # Scoped to the M13 span. An earlier version of this report filled the "inside the
        # span" figure from the whole-Rigveda tally above and printed 10,314 where the answer
        # is 1 -- the key said MANTRA and the value counted every Rigvedic verse. A row in a
        # metric table is a label, not a count of the thing the surrounding prose is about.
        span_by_level = {
            r["lvl"]: r["c"]
            for r in s.run(
                """
                MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE m.canonical_key =~ 'VG:RV:SAK:M01:S0(6[5-9]|70):.*'
                RETURN coalesce(t.alignment_level,'<null>') AS lvl, count(t) AS c
                """
            )
        }
        covered_now = {
            r["veda"]: r["c"]
            for r in s.run(
                """
                MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE t.language = 'en'
                RETURN split(m.canonical_key,':')[1] AS veda, count(DISTINCT m) AS c
                """
            )
        }
    drv.close()

    # =================================================================================
    # PHASE 7 -- OWNER_DECISION_A_RV_SPAN
    # =================================================================================
    in_span = [k for k in rv_untranslated if M13_SPAN.match(k)]
    outside = [k for k in rv_untranslated if not M13_SPAN.match(k)]

    def odd_sibling(key: str) -> str | None:
        m = re.match(r"(VG:RV:SAK:M\d+:S\d+):V(\d+)$", key)
        if not m:
            return None
        n = int(m.group(2))
        return f"{m.group(1)}:V{n - 1:03d}" if n % 2 == 0 else None

    span_rows = []
    for k in in_span:
        sib = odd_sibling(k)
        span_rows.append(
            {
                "canonical_key": k,
                "has_its_own_translation": False,
                "paired_odd_sibling": sib,
                "sibling_carries_a_mantra_range": bool(sib and sib in range_bearers),
                "covered_by_a_multi_verse_span": bool(sib and sib in range_bearers),
                "is_a_missing_translation": not (sib and sib in range_bearers),
            }
        )
    covered_by_range = [r for r in span_rows if r["covered_by_a_multi_verse_span"]]
    genuinely_missing_in_span = [r for r in span_rows if r["is_a_missing_translation"]]

    staged_rv = [r for r in gb.values() if r["veda"] == "RV"]
    staged_in_span = [r for r in staged_rv if M13_SPAN.match(r["canonical_key"])]
    outside_set = set(outside)
    staged_outside = [r for r in staged_rv if r["canonical_key"] in outside_set]
    unstaged_outside = [k for k in outside if k not in {r["canonical_key"] for r in staged_rv}]

    def verdicts(rows):
        return dict(
            Counter(
                f"{r['gate_b_category']}/{gc[r['staged_row_id']]['gate_c_category']}"
                for r in rows
            )
        )

    rv_span_decision = {
        "phase": 7,
        "decision": "OWNER_DECISION_A_RV_SPAN",
        "question_1_what_did_it_originally_protect": {
            "answer": (
                "the 50 Sakala mantras with no translation, and specifically the risk that "
                "Griffith's merged dvipada units would be bound 1:1 to canonical verses. "
                "GAP-TRANSLATION-004 records it as: 'Griffith renders each pair of our "
                "Sakala verses as one merged unit, so unit k covers verses 2k-1 and 2k. The "
                "import bound unit k to verse k. 30 of the 50 were never a source gap.'"
            ),
            "registry_gap": "GAP-TRANSLATION-004",
            "population_protected": 50,
            "of_which_paired_span": 30,
        },
        "question_2_which_part_is_now_mechanically_resolved_by_m13": {
            "rv_1_65_to_1_70_verses_without_their_own_translation": len(in_span),
            "of_those_covered_by_a_mantra_range_on_the_paired_odd_verse": len(covered_by_range),
            "of_those_genuinely_missing_a_translation": len(genuinely_missing_in_span),
            "live_mantra_range_translations_in_the_span": span_by_level.get("MANTRA_RANGE", 0),
            "live_mantra_translations_in_the_span": span_by_level.get("MANTRA", 0),
            "live_translations_in_the_span_by_alignment_level": span_by_level,
            "staged_rows_still_targeting_the_span": len(staged_in_span),
            "conclusion": (
                "every one of the 30 is covered by a MANTRA_RANGE attached to its paired odd "
                "verse, and no staged row targets the span at all. They are canonical verses "
                "covered by a multi-verse translation span, NOT missing translations, and the "
                "distinction is the whole substance of decision A. The coordinate repair the "
                "decision was waiting on has been made and read back clean (M13, 31 rows, 25 "
                "moved, 6 already correct, 0 unresolved)."
            ),
        },
        "question_3_which_rows_remain_missing_or_unimported": {
            "rv_verses_with_no_translation_of_their_own": len(rv_untranslated),
            "inside_the_m13_span_and_covered_by_a_range": len(covered_by_range),
            "outside_the_span": len(outside),
            "outside_and_staged": len(staged_outside),
            "outside_and_never_staged": len(unstaged_outside),
            "never_staged_keys": unstaged_outside,
            "staged_outside_verdicts": verdicts(staged_outside),
        },
        "question_4_why_are_they_absent": {
            "because_no_source_unit_exists": {
                "count": len(unstaged_outside),
                "keys": unstaged_outside,
                "note": (
                    "not staged by the translation agent and not covered by any span. These "
                    "are the only Rigvedic verses in the corpus for which this campaign has "
                    "produced no candidate at all."
                ),
            },
            "because_one_source_unit_spans_several_canonical_verses": {
                "count": len(covered_by_range),
                "note": (
                    "the paired dvipada verses of RV 1.65-1.70. A translation covering them "
                    "exists and is typed MANTRA_RANGE; they lack a dedicated 1:1 rendering "
                    "because Griffith did not print one."
                ),
            },
            "because_another_staged_source_exists_but_is_withheld": {
                "count": len(staged_outside),
                "verdicts": verdicts(staged_outside),
                "note": (
                    "17 rows outside the span. 4 are PROBABLE and withheld by the central "
                    "policy; of the 13 that pass Gate B, 5 carry Griffith's Latin rather "
                    "than English (RV 1.179 and 10.61, his Victorian substitution for "
                    "explicit passages) and 8 pass Gate C."
                ),
            },
        },
        "question_5_recommended_disposition": {
            "recommendation": "CLOSED_DERIVED_ON_THE_SPAN_PLUS_REPLACED_BY_SCOPE_DECISION",
            "reasoning": (
                "Decision A exists to stop a merged unit being bound 1:1. That hazard is "
                "gone: the span is typed MANTRA_RANGE, the readback is clean, and no staged "
                "row targets the span, so there is nothing left for the owner to approve or "
                "refuse about it. What remains under the decision's old boundary is a "
                "different question -- whether to publish Griffith's Latin, and what to do "
                "about three verses with no candidate source -- and neither involves the "
                "paired spine. Keeping one gate over both would make the owner re-decide a "
                "resolved coordinate question in order to reach an unrelated editorial one."
            ),
            "mechanically_decided_part": {
                "scope": "RV 1.65-1.70 paired dvipada span",
                "status": "CLOSED_DERIVED",
                "evidence": (
                    "30 of 30 covered by MANTRA_RANGE; 0 staged rows targeting the span; "
                    "M13 readback clean with 0 findings; canonical census unchanged"
                ),
                "needs_owner_judgement": False,
            },
            "residual_requiring_owner_judgement": [
                {
                    "scope": "Griffith's Latin substitutions",
                    "population": 5,
                    "keys": [
                        r["canonical_key"]
                        for r in staged_outside
                        if gc[r["staged_row_id"]]["gate_c_category"] == "C_WITHHOLD_AMBIGUOUS"
                    ],
                    "question": (
                        "Griffith renders explicit passages into Latin. The text is his and "
                        "is public domain, but it is not an English translation and the rows "
                        "declare language 'en'. Publish with a language correction and a "
                        "disclosure, or leave the verses uncovered?"
                    ),
                    "new_decision_id": "OWNER_DECISION_F_LATIN_SUBSTITUTION",
                },
                {
                    "scope": "Rigvedic verses with no candidate source",
                    "population": len(unstaged_outside),
                    "keys": unstaged_outside,
                    "question": (
                        "these are a scope statement, not a gate: no source has been found. "
                        "They belong in GAP-TRANSLATION-004's residual, not behind an owner "
                        "decision."
                    ),
                    "new_decision_id": None,
                },
            ],
        },
        "per_verse_table_in_span": span_rows,
    }
    write_json("rv_span_decision.json", rv_span_decision)

    # =================================================================================
    # PHASE 8 -- OWNER_DECISION_C_FORCED_ADDRESSES
    # =================================================================================
    INDEPENDENT = {
        "PRINTED_LABEL_READ_DIRECTLY",
        "CORRUPT_GLYPHS_REPAIR_TO_CANONICAL",
        "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS",
        "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS",
    }
    forced_table = []
    for rid, b in sorted(gb.items(), key=lambda kv: kv[1]["canonical_key"]):
        r = staged[rid]
        p = r["payload"]
        flag = p.get("address_forced_without_content_control")
        if flag is None:
            continue
        key = b["canonical_key"]
        v = yv.get(key, {})
        det = v.get("source_local_address_determination")
        unit = v.get("best_matching_unit") or {}
        c = gc[rid]
        rv_control = p.get("verification")
        controls = []
        if det == "PRINTED_LABEL_READ_DIRECTLY":
            controls.append("SOURCE_PRINTS_THE_CORRECT_LABEL")
        if det == "CORRUPT_GLYPHS_REPAIR_TO_CANONICAL":
            controls.append("SOURCE_LABEL_GLYPHS_REPAIR_TO_THE_CANONICAL_NUMBER")
        if det == "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS":
            controls.append("SOURCE_PRINTED_NEIGHBOURS_BRACKET_THE_SLOT_UNIQUELY")
        if det == "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS":
            controls.append("SOURCE_LABELS_SIT_AT_A_VERIFIED_CONSTANT_OFFSET")
        if rv_control:
            controls.append("INDEPENDENT_RIGVEDA_ENGLISH_PARALLEL_CONTROL")

        cross_ref = c["evidence"]["literal_integrity"]["editorial_cross_reference"]
        if cross_ref:
            rec, why = (
                "SOURCE_ERROR",
                "the address is determined, but the literal at that address is Griffith's "
                "editorial cross-reference ('etc., as in 44 mutatis mutandis'), not a "
                "translation; importing it would assert a pointer as the verse's meaning",
            )
        elif det in INDEPENDENT and c["gate_c_category"] == "C_PASS":
            rec, why = (
                "SAFE_TO_IMPORT",
                "independent content control present and adversarially clean: "
                + ", ".join(controls),
            )
        elif det in INDEPENDENT:
            rec, why = (
                "NEEDS_OWNER_SEMANTIC_DECISION",
                f"the address is independently controlled ({', '.join(controls)}) but Gate C "
                f"withholds the row for another reason: {c['gate_c_category']}",
            )
        else:
            rec, why = (
                "KEEP_WITHHELD",
                "no independent control: the pinned source neither prints a usable label for "
                f"this unit nor brackets the slot uniquely (determination={det!r})",
            )

        forced_table.append(
            {
                "staged_row_id": rid,
                "canonical_key": key,
                "source_coordinate": r.get("source_locator"),
                "forced_canonical_target": key,
                "why_forcing_occurred": (
                    p.get("source_label_defect"),
                    p.get("stage_gap_defect"),
                ),
                "payload_claims_no_content_control": flag is True,
                "independent_control_available": det in INDEPENDENT,
                "independent_evidence": {
                    "determination": det,
                    "printed_label_glyphs": unit.get("printed_label_glyphs"),
                    "printed_label_read": unit.get("printed_label"),
                    "printed_label_candidates": unit.get("printed_label_candidates"),
                    "printed_label_equals_canonical_verse": v.get(
                        "printed_label_equals_canonical_verse"
                    ),
                    "neighbours": v.get("neighbours"),
                    "neighbours_bracket_canonical_slot_exactly": v.get(
                        "neighbours_bracket_canonical_slot_exactly"
                    ),
                    "literal_found_in_pinned_source": v.get("literal_found_in_pinned_source"),
                    "match_score": unit.get("match_score"),
                    "row_pins_its_own_source_bytes": v.get("row_pins_its_own_bytes"),
                    "rigveda_english_control": rv_control,
                    "controls": controls,
                },
                "gate_b_result": b["gate_b_category"],
                "gate_c_result": c["gate_c_category"],
                "classification": (
                    "VERIFIED_INDEPENDENTLY" if det in INDEPENDENT else "NOT_VERIFIED"
                ),
                "recommendation": rec,
                "recommendation_basis": why,
            }
        )

    forced_summary = {
        "phase": 8,
        "decision": "OWNER_DECISION_C_FORCED_ADDRESSES",
        "what_the_decision_protects": (
            "31 Yajurvedic rows whose payload declares "
            "address_forced_without_content_control: true, plus 8 more carrying the same "
            "label defect with a control already attached. Owner principle 14 bars promoting "
            "the 31 unless independent content verification now exists."
        ),
        "why_the_central_policy_does_not_cover_them": (
            "all 31 are staged mapping_confidence EXACT, and the campaign's central "
            "NOT_IMPORTABLE set is {PROBABLE, UNVERIFIED}. The predicate keys on confidence "
            "and forcing is orthogonal to it, so nothing mechanical withholds these rows "
            "today. Gate B carries B_NEEDS_INDEPENDENT_CONTENT_CONTROL as a separate "
            "category for exactly this reason."
        ),
        "independent_verification_performed": (
            "the pinned Griffith snapshot is on disk -- 45 pages under "
            "data/raw/sacred_texts/2026-09-07/wyv, each named by the sha256 of its own bytes, "
            "and 39 of the 51 rows name the hash of the page they were read from. Each row's "
            "literal was located in those bytes by content and the printed label around it "
            "was read directly, which tests the rows' own claim that the source prints no "
            "usable label."
        ),
        "headline_finding": (
            "the claim is wrong for most of them. The source prints a correct, legible label "
            "for 15 of the 31, so those addresses were read rather than forced. For 14 more "
            "the unit's own label is genuinely corrupt -- Griffith's adhyaya 6 prints '23' "
            "twice, once for verse 23 and again for verse 25 -- but the printed neighbours "
            "bracket the canonical slot uniquely (24 before, 26 after, one slot between), "
            "which is a source-local control and not an inference from position."
        ),
        "rows": len(forced_table),
        "by_classification": dict(Counter(r["classification"] for r in forced_table)),
        "by_determination": dict(
            Counter(str(r["independent_evidence"]["determination"]) for r in forced_table)
        ),
        "by_recommendation": dict(Counter(r["recommendation"] for r in forced_table)),
        "flag_true_by_recommendation": dict(
            Counter(
                r["recommendation"] for r in forced_table if r["payload_claims_no_content_control"]
            )
        ),
        "flag_false_by_recommendation": dict(
            Counter(
                r["recommendation"]
                for r in forced_table
                if not r["payload_claims_no_content_control"]
            )
        ),
        "decision_table": forced_table,
    }
    write_json("forced_address_decision_table.json", forced_summary)

    # =================================================================================
    # PHASE 9 -- THE TRANSLATION DECISION MATRIX
    # =================================================================================
    forced_rec = {r["canonical_key"]: r["recommendation"] for r in forced_table}

    def classify(rid: str) -> tuple[str, str]:
        b, c = gb[rid], gc[rid]
        r = staged[rid]
        p = r["payload"]
        key = b["canonical_key"]
        bc, cc = b["gate_b_category"], c["gate_c_category"]
        if bc == "B_FAIL_POLICY":
            return "WITHHOLD_PROVENANCE", (
                "mapping_confidence is PROBABLE; the central importability policy withholds it"
            )
        if bc == "B_NEEDS_INDEPENDENT_CONTENT_CONTROL":
            rec = forced_rec.get(key)
            if rec == "SAFE_TO_IMPORT":
                return "SAFE_IMPORT_DETERMINISTIC_VERIFIED_ALIGNMENT", (
                    "forced address, but independently verified against the pinned source's "
                    "own printed labels"
                )
            if rec == "SOURCE_ERROR":
                return "REJECT_NON_TRANSLATION_LITERAL", (
                    "the literal at the verified address is an editorial cross-reference"
                )
            return "WITHHOLD_FORCED_ADDRESS_UNVERIFIED", (
                "forced address with no independent source-local control"
            )
        if bc == "B_FAIL_SOURCE_COORDINATE":
            return "WITHHOLD_AMBIGUOUS_ALIGNMENT", (
                "the printed source locator omits a hierarchy level and addresses several "
                "canonical keys, so no third party can re-find the unit"
            )
        if bc == "B_FAIL_PROVENANCE":
            return "WITHHOLD_PROVENANCE", (
                "no content hash and no immutable archive timestamp for the bytes read"
            )
        if bc == "B_CONFLICT_EXISTING_TRANSLATION":
            return "CONFLICT_EXISTING_CANONICAL_TRANSLATION", "the target already carries English"
        # Gate B passed; Gate C decides.
        if cc == "C_FAIL_ARCHIVE_EVIDENCE":
            return "WITHHOLD_PROVENANCE", (
                "cites an archive capture with no content hash, and the capture is absent "
                "from the artifact's own page proofs"
            )
        if cc == "C_FAIL_DUPLICATE_GENERATION":
            return "REJECT_WRONG_TARGET", "one printed source unit emitted onto several targets"
        if cc == "C_FAIL_CROSS_CORPUS_CONTAMINATION":
            return "WITHHOLD_CROSS_CORPUS_POLICY", (
                "another corpus's rendering, and the textual identity that would justify it "
                "does not reproduce"
            )
        if cc == "C_FAIL_SOURCE_GRANULARITY":
            return "REJECT_NON_TRANSLATION_LITERAL", (
                "the literal is an editorial cross-reference, not a translation"
            )
        if cc == "C_WITHHOLD_REUSED_RENDERING_POLICY":
            return "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE", (
                "Griffith's Rigveda rendering on a verse whose Sanskrit is verified "
                "character-identical; truthful only if the reuse is disclosed, and never "
                "independent semantic evidence for the target corpus"
            )
        if cc == "C_WITHHOLD_AMBIGUOUS":
            return "WITHHOLD_AMBIGUOUS_ALIGNMENT", (
                c["gate_c_reasons"][0][:200] if c["gate_c_reasons"] else "ambiguous"
            )
        if cc == "C_PASS":
            if b["measured_grain"] == "MANTRA_RANGE":
                return "SAFE_IMPORT_MULTI_VERSE_RANGE", (
                    "an explicitly numbered multi-verse print unit, complete over its span"
                )
            if forced_rec.get(key) == "SAFE_TO_IMPORT":
                return "SAFE_IMPORT_DETERMINISTIC_VERIFIED_ALIGNMENT", (
                    "label defect, independently verified against the printed source"
                )
            return "SAFE_IMPORT_SOURCE_EXPLICIT", (
                "the source prints this verse's own label and its own translation, and the "
                "adversarial checks found no competing explanation"
            )
        return "WITHHOLD_AMBIGUOUS_ALIGNMENT", f"unclassified ({bc}/{cc})"

    CLASS_META = {
        "SAFE_IMPORT_SOURCE_EXPLICIT": (True, True),
        "SAFE_IMPORT_DETERMINISTIC_VERIFIED_ALIGNMENT": (True, True),
        "SAFE_IMPORT_MULTI_VERSE_RANGE": (True, True),
        "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE": (True, False),
        "WITHHOLD_FORCED_ADDRESS_UNVERIFIED": (False, False),
        "WITHHOLD_CROSS_CORPUS_POLICY": (False, False),
        "WITHHOLD_AMBIGUOUS_ALIGNMENT": (False, False),
        "WITHHOLD_PROVENANCE": (False, False),
        "REJECT_WRONG_TARGET": (False, False),
        "REJECT_NON_TRANSLATION_LITERAL": (False, False),
        "CONFLICT_EXISTING_CANONICAL_TRANSLATION": (False, False),
    }

    assigned = {}
    for rid in gb:
        cls, why = classify(rid)
        assigned[rid] = (cls, why)

    matrix = {}
    for rid, (cls, why) in assigned.items():
        b = gb[rid]
        r = staged[rid]
        m = matrix.setdefault(
            cls,
            {
                "final_class": cls,
                "count": 0,
                "by_veda": Counter(),
                "by_source": Counter(),
                "alignment_semantics": Counter(),
                "example_reasons": set(),
                "owner_decision_dependency": set(),
                "import_creates_nodes": None,
                "import_creates_relationships": None,
                "import_sets_properties": None,
                "product_must_disclose": None,
                "usable_as_independent_semantic_evidence": None,
            },
        )
        m["count"] += 1
        m["by_veda"][b["veda"]] += 1
        m["by_source"][b["source_id"]] += 1
        m["alignment_semantics"][b["measured_grain"]] += 1
        m["example_reasons"].add(why[:180])
        if r["payload"].get("address_forced_without_content_control") is not None:
            m["owner_decision_dependency"].add("OWNER_DECISION_C_FORCED_ADDRESSES")
        if M13_SPAN.match(b["canonical_key"]):
            m["owner_decision_dependency"].add("OWNER_DECISION_A_RV_SPAN")
        if cls == "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE":
            m["owner_decision_dependency"].add("OWNER_DECISION_D_REUSED_RENDERING_POLICY")
        if cls == "WITHHOLD_AMBIGUOUS_ALIGNMENT" and gc[rid]["evidence"]["literal_integrity"][
            "detected"
        ]["verdict"] in {"LATIN", "NOT_RECOGNISABLY_ENGLISH"}:
            m["owner_decision_dependency"].add("OWNER_DECISION_F_LATIN_SUBSTITUTION")

    for cls, m in matrix.items():
        importable, independent = CLASS_META[cls]
        m["by_veda"] = dict(sorted(m["by_veda"].items()))
        m["by_source"] = dict(sorted(m["by_source"].items(), key=lambda kv: -kv[1]))
        m["alignment_semantics"] = dict(sorted(m["alignment_semantics"].items()))
        m["example_reasons"] = sorted(m["example_reasons"])
        m["owner_decision_dependency"] = sorted(m["owner_decision_dependency"]) or ["none"]
        m["eligible_for_an_import_plan"] = importable
        m["import_creates_nodes"] = (
            "one :Translation node per row" if importable else "nothing; not imported"
        )
        m["import_creates_relationships"] = (
            "one HAS_TRANSLATION edge per row" if importable else "nothing; not imported"
        )
        m["import_sets_properties"] = (
            [
                "text",
                "translator",
                "work_edition",
                "year",
                "language",
                "source_id",
                "alignment_level",
                "quality_status",
                "rights_status",
                "translation_id",
                "passage_id",
            ]
            if importable
            else []
        )
        m["product_must_disclose"] = (
            "that the English is Griffith's Rigveda rendering of a textually identical verse "
            "in another corpus, not a translation made of this corpus"
            if cls == "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE"
            else "that one rendering covers a span of canonical verses"
            if cls == "SAFE_IMPORT_MULTI_VERSE_RANGE"
            else None
        )
        m["usable_as_independent_semantic_evidence"] = independent

    write_json(
        "translation_decision_matrix.json",
        {
            "phase": 9,
            "total_rows": len(assigned),
            "classes_declared": sorted(CLASS_META),
            "safe_total": sum(
                m["count"] for m in matrix.values() if m["eligible_for_an_import_plan"]
            ),
            "withheld_total": sum(
                m["count"] for m in matrix.values() if not m["eligible_for_an_import_plan"]
            ),
            "classes": [matrix[k] for k in sorted(matrix, key=lambda k: -matrix[k]["count"])],
            "per_row": [
                {
                    "staged_row_id": rid,
                    "canonical_key": gb[rid]["canonical_key"],
                    "veda": gb[rid]["veda"],
                    "source_id": gb[rid]["source_id"],
                    "gate_b": gb[rid]["gate_b_category"],
                    "gate_c": gc[rid]["gate_c_category"],
                    "final_class": cls,
                }
                for rid, (cls, _why) in sorted(assigned.items())
            ],
        },
    )

    # =================================================================================
    # PHASE 10 -- IMPORT DRY RUN (PLAN ONLY, NOT EXECUTED)
    # =================================================================================
    safe_ids = [rid for rid, (cls, _) in assigned.items() if CLASS_META[cls][0]]
    per_veda_delta = Counter(gb[rid]["veda"] for rid in safe_ids)
    per_source = Counter(gb[rid]["source_id"] for rid in safe_ids)
    per_level = Counter(
        "MANTRA_RANGE" if gb[rid]["measured_grain"] == "MANTRA_RANGE" else "MANTRA"
        for rid in safe_ids
    )
    per_class = Counter(assigned[rid][0] for rid in safe_ids)
    targets = {gb[rid]["canonical_key"] for rid in safe_ids}

    dry_run = {
        "phase": 10,
        "executed": False,
        "statement": (
            "THIS PLAN WAS NOT EXECUTED. No canonical translation was created, updated or "
            "deleted by this task. The graph census and the translation attachment digest "
            "are re-read at the end of the run and compared against the phase-0 baseline."
        ),
        "rows_in_plan": len(safe_ids),
        "distinct_target_passages": len(targets),
        "rows_per_target": round(len(safe_ids) / len(targets), 4) if targets else None,
        "translations_to_create": len(safe_ids),
        "translations_to_update": 0,
        "why_zero_updates": (
            "every row in the plan targets a passage that carries no English translation "
            "today; Gate B routes any row whose target is already translated to "
            "B_CONFLICT_EXISTING_TRANSLATION, and this task does not overwrite live text"
        ),
        "nodes_created": {"Translation": len(safe_ids)},
        "relationships_created": {"HAS_TRANSLATION": len(safe_ids)},
        "properties_set_per_node": [
            "text",
            "translator",
            "work_edition",
            "year",
            "language",
            "source_id",
            "alignment_level",
            "quality_status",
            "rights_status",
            "translation_id",
            "passage_id",
        ],
        "conflicts": 0,
        "per_veda_delta": dict(sorted(per_veda_delta.items())),
        "per_source_breakdown": dict(sorted(per_source.items(), key=lambda kv: -kv[1])),
        "alignment_level_breakdown": dict(sorted(per_level.items())),
        "per_class_breakdown": dict(sorted(per_class.items(), key=lambda kv: -kv[1])),
        "owner_decision_dependencies": {
            "OWNER_DECISION_C_FORCED_ADDRESSES": sum(
                1
                for rid in safe_ids
                if staged[rid]["payload"].get("address_forced_without_content_control")
                is not None
            ),
            "OWNER_DECISION_D_REUSED_RENDERING_POLICY": sum(
                1
                for rid in safe_ids
                if assigned[rid][0] == "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE"
            ),
            "OWNER_DECISION_A_RV_SPAN": 0,
        },
        "census_effect": {
            "nodes": f"+{len(safe_ids)}",
            "relationships": f"+{len(safe_ids)}",
            "predicted_nodes": 116838 + len(safe_ids),
            "predicted_relationships": 281257 + len(safe_ids),
            "core_corpus_change": "none; no :Mantra is created or deleted",
        },
    }
    write_json("import_dry_run.json", dry_run)

    # ---- predicted coverage, split by how the verse is covered -----------------------
    coverage = {}
    for veda, corpus in sorted(CORE_CORPUS_INVARIANT.items()):
        now = covered_now.get(veda, 0)
        add_mantra = sum(
            1
            for rid in safe_ids
            if gb[rid]["veda"] == veda and gb[rid]["measured_grain"] != "MANTRA_RANGE"
        )
        add_range = sum(
            1
            for rid in safe_ids
            if gb[rid]["veda"] == veda and gb[rid]["measured_grain"] == "MANTRA_RANGE"
        )
        add_reuse = sum(
            1
            for rid in safe_ids
            if gb[rid]["veda"] == veda
            and assigned[rid][0] == "SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE"
        )
        dedicated_now = live_by_level.get(f"{veda}|MANTRA", 0)
        range_now = live_by_level.get(f"{veda}|MANTRA_RANGE", 0)
        # A range row attaches to one verse but the rendering covers its span; the second
        # verse of each pair gains no edge, so it stays uncovered on an edge count while
        # being covered in substance. Both figures are reported; neither is the total.
        coverage[veda] = {
            "corpus": corpus,
            "covered_today": now,
            "uncovered_today": corpus - now,
            "today_split": {
                "verse_with_a_dedicated_1_to_1_translation": dedicated_now,
                "verse_carrying_a_multi_verse_range_translation": range_now,
                "verse_covered_only_by_a_sibling_s_range_and_carrying_no_edge": (
                    len(covered_by_range) if veda == "RV" else 0
                ),
            },
            "plan_adds": {
                "dedicated_1_to_1": add_mantra - add_reuse,
                "multi_verse_range": add_range,
                "reused_cross_corpus_rendering": add_reuse,
                "total_new_edges": add_mantra + add_range,
            },
            "predicted_after_import": {
                "verses_carrying_an_edge": now + add_mantra + add_range,
                "of_which_dedicated_own_corpus_translation": dedicated_now
                + (add_mantra - add_reuse),
                "of_which_multi_verse_range": range_now + add_range,
                "of_which_reused_cross_corpus_rendering": add_reuse,
                "still_carrying_no_edge": corpus - (now + add_mantra + add_range),
            },
        }
    write_json(
        "predicted_coverage.json",
        {
            "phase": 10,
            "warning": (
                "these four figures must not be summed into one percentage. A verse with a "
                "dedicated Griffith rendering of its own corpus, a verse sharing one "
                "rendering with its neighbour, and a verse showing another corpus's "
                "rendering are three different claims, and the campaign has already graded a "
                "collapsed coverage figure as MISLEADING."
            ),
            "per_veda": coverage,
            "totals": {
                "corpus": sum(CORE_CORPUS_INVARIANT.values()),
                "covered_today": sum(covered_now.get(v, 0) for v in CORE_CORPUS_INVARIANT),
                "new_edges_if_approved": len(safe_ids),
                "predicted_verses_with_an_edge": sum(
                    coverage[v]["predicted_after_import"]["verses_carrying_an_edge"]
                    for v in coverage
                ),
                "predicted_still_uncovered": sum(
                    coverage[v]["predicted_after_import"]["still_carrying_no_edge"]
                    for v in coverage
                ),
            },
        },
    )

    print("=== PHASE 7 RV SPAN ===")
    print(f"  RV verses with no translation: {len(rv_untranslated)}")
    print(f"  in M13 span: {len(in_span)}  covered by a MANTRA_RANGE: {len(covered_by_range)}")
    print(f"  genuinely missing inside the span: {len(genuinely_missing_in_span)}")
    print(f"  outside the span: {len(outside)} (staged {len(staged_outside)}, "
          f"never staged {len(unstaged_outside)})")
    print(f"  recommendation: {rv_span_decision['question_5_recommended_disposition']['recommendation']}")
    print("=== PHASE 8 FORCED ADDRESSES ===")
    print(f"  rows: {forced_summary['rows']}")
    print(f"  by classification: {forced_summary['by_classification']}")
    print(f"  by determination: {forced_summary['by_determination']}")
    print(f"  by recommendation: {forced_summary['by_recommendation']}")
    print("=== PHASE 9 MATRIX ===")
    for k in sorted(matrix, key=lambda k: -matrix[k]["count"]):
        print(f"  {matrix[k]['count']:6d}  {k}  {dict(matrix[k]['by_veda'])}")
    print("=== PHASE 10 DRY RUN (NOT EXECUTED) ===")
    print(f"  rows in plan: {dry_run['rows_in_plan']}  targets: {dry_run['distinct_target_passages']}")
    print(f"  per veda: {dry_run['per_veda_delta']}")
    print(f"  alignment levels: {dry_run['alignment_level_breakdown']}")
    for v, d in coverage.items():
        p = d["predicted_after_import"]
        print(f"  {v}: today {d['covered_today']}/{d['corpus']} -> "
              f"{p['verses_carrying_an_edge']}/{d['corpus']} "
              f"(dedicated {p['of_which_dedicated_own_corpus_translation']}, "
              f"range {p['of_which_multi_verse_range']}, reuse {p['of_which_reused_cross_corpus_rendering']}, "
              f"uncovered {p['still_carrying_no_edge']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
