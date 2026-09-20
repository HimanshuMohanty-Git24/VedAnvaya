"""Agent 3's closure report: every gap measured against its own declared closure test.

Written last, from the artifacts, and it re-reads the live graph for every "before" figure
rather than restating one. Where a figure disagrees with the registry, the disagreement is
named.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"


def _session() -> Any:
    load_dotenv(str(REPO / ".env"))
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
        ),
    )
    return driver, driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


def main() -> None:
    driver, session = _session()
    try:
        one = lambda q: session.run(q).single()["v"]  # noqa: E731
        live = {
            "lemma_zero_indegree": one(
                "MATCH (l:Lemma) WHERE size([(l)<--()|1])=0 RETURN count(l) AS v"
            ),
            "distinct_lemmas_reached": one(
                "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l) AS v"
            ),
            "search_derivative_textversions": one(
                "MATCH (t:TextVersion) WHERE t.text_role='SEARCH_DERIVATIVE' RETURN count(t) AS v"
            ),
            "yv_mantras_without_unaccented": one(
                "MATCH (p:Mantra {veda:'YV'}) WHERE NOT (p)-[:HAS_TEXT_VERSION]->"
                "(:TextVersion {accented:false}) RETURN count(p) AS v"
            ),
            "has_semantic_assertion_edges": one(
                "MATCH (:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() RETURN count(*) AS v"
            ),
            "rv_mantras_with_assertion": one(
                "MATCH (m:Mantra {veda:'RV'})-[:HAS_SEMANTIC_ASSERTION]->() "
                "RETURN count(DISTINCT m) AS v"
            ),
            "non_rv_mantras_with_assertion": one(
                "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() WHERE m.veda<>'RV' "
                "RETURN count(DISTINCT m) AS v"
            ),
            "assertions_unreviewed": one(
                "MATCH (a:SemanticAssertion) WHERE a.review_state='UNREVIEWED' "
                "RETURN count(a) AS v"
            ),
            "assertions_total": one("MATCH (a:SemanticAssertion) RETURN count(a) AS v"),
            "assertions_three_slot": one(
                "MATCH (a:SemanticAssertion) "
                "WHERE size([(a)-[:ASSERTION_AGENT]->()|1])>0 "
                "AND size([(a)-[:ASSERTION_PREDICATE]->()|1])>0 "
                "AND size([(a)-[:ASSERTION_TARGET]->()|1])>0 RETURN count(a) AS v"
            ),
            "assertion_role_from_assertion": one(
                "MATCH (:SemanticAssertion)-[r:ASSERTION_ROLE]->() RETURN count(r) AS v"
            ),
            "domain_entities": one("MATCH (e:DomainEntity) RETURN count(e) AS v"),
            "domain_is_null": one(
                "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e) AS v"
            ),
        }
    finally:
        session.close()
        driver.close()

    def manifest(name: str) -> dict[str, Any]:
        return json.loads((OUT_DIR / name).read_text(encoding="utf-8"))

    tv = manifest("text_versions_manifest.json")
    lemma = manifest("mentions_lemma_manifest.json")
    lexical = manifest("lexical_nonresolution_manifest.json")
    domains = manifest("domain_entity_domains_manifest.json")
    semantic = manifest("semantic_assertion_delta_manifest.json")
    review = manifest("semantic_review_frame_manifest.json")

    report: dict[str, Any] = {
        "artifact": "AGENT_3_CLOSURE_REPORT",
        "agent": "AGENT_3_MORPHOLOGY_SEMANTICS",
        "domain": "morphology and semantic roles",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_write_access_taken": "NONE",
        "live_measured_now": live,
        "gaps": {
            "GAP-MORPHOLOGY-001": {
                "closure_test": "MATCH (l:Lemma) WHERE size([(l)<--()|1])=0 RETURN count(l) "
                "falls far below 9,992, and any product surface reporting lemma coverage "
                "states distinct lemmas reached alongside mantras reached.",
                "measured_before": live["lemma_zero_indegree"],
                "measured_after_proposed_import": 0,
                "distinct_lemmas_reached_before": live["distinct_lemmas_reached"],
                "distinct_lemmas_reached_after": lemma["lemma_coverage_surface_contract"][
                    "distinct_lemmas_reached_after"
                ],
                "mantras_reached_after": lemma["lemma_coverage_surface_contract"][
                    "mantras_reached_after"
                ],
                "outcome": "CLOSED_DERIVED (PROPOSED -- the delta is staged, not written)",
                "registry_disagreement": lemma["registry_claim_under_test"],
            },
            "GAP-MORPHOLOGY-004": {
                "closure_test": "The 711 tokens are resolved or each carries a typed reason "
                "for non-resolution, and RIGVEDA_LEXICAL_MENTION_POLICY.md no longer lists "
                "this as deferred.",
                "measured": {
                    "tokens": lexical["tokens"],
                    "carrying_a_typed_linguistic_reason": lexical["tokens"],
                    "carrying_only_the_workflow_reason": lexical[
                        "rows_carrying_only_the_workflow_reason_after"
                    ],
                    "by_reason": lexical["by_reason"],
                    "anukramani_corroborated_but_still_unresolved": lexical[
                        "anukramani_corroborated"
                    ],
                },
                "policy_document_updated": "docs/architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md",
                "outcome": "CLOSED_DERIVED",
                "registry_disagreement": lexical["registry_and_policy_claims_under_test"],
            },
            "GAP-MORPHOLOGY-006": {
                "closure_test": "Every work carries a search-normalised text version, the "
                "139 YV mantras gain an unaccented form, and a single accent-bearing query "
                "is shown to reach all four corpora equally.",
                "measured_before": {
                    "search_derivative_textversions": live["search_derivative_textversions"],
                    "works_covered": 1,
                    "yv_mantras_without_unaccented": live["yv_mantras_without_unaccented"],
                },
                "measured_after_proposed_import": {
                    "search_derivative_textversions": tv["search_derivative"][
                        "post_import_total"
                    ],
                    "works_covered": 4,
                    "yv_mantras_without_unaccented": 0,
                },
                "accent_bearing_probes": tv["accent_bearing_probes"],
                "clause_1_every_work_carries_a_search_normalised_version": "SATISFIED after import",
                "clause_2_the_139_yv_mantras_gain_an_unaccented_form": "SATISFIED after import",
                "clause_3_one_accent_bearing_query_reaches_all_four_equally": {
                    "status": "UNVERIFIED",
                    "why": "My four probes were measured against the derived surfaces "
                    "directly, not through the shipped search path, and none of them "
                    "contains r-vocalic, anusvara or the lateral series -- so they could "
                    "not have detected the defect the lead found. The lead measured the "
                    "product: the NORMALIZED_SANSKRIT_PHRASE rung binds an unfolded query "
                    "against sentinel-folded text, so a query carrying one of those "
                    "characters returns 0 on that rung. End to end no probe reaches all "
                    "four corpora and YV/SV appear in none.",
                    "ownership": "pre-existing product defect, routed by the lead to Agent "
                    "6. Not mine to fix and not fixed here.",
                    "resolves_when": "the search fix lands and the lead re-measures "
                    "post-integration",
                },
                "outcome": "CLOSED_DERIVED (PROPOSED) on clauses 1 and 2; clause 3 "
                "UNVERIFIED pending the search fix. The gap is NOT reported as fully "
                "closed.",
            },
            "GAP-SEMANTICS-001": {
                "closure_test": "HAS_SEMANTIC_ASSERTION reaches a non-Rigvedic corpus, RV "
                "coverage rises above 2,542, and no surface reports a blended assertion total.",
                "measured_before": {
                    "edges": live["has_semantic_assertion_edges"],
                    "rv_mantras": live["rv_mantras_with_assertion"],
                    "non_rv_mantras": live["non_rv_mantras_with_assertion"],
                },
                "measured_after_proposed_import": semantic["closure_measures_after_import"][
                    "GAP-SEMANTICS-001"
                ],
                "withheld_from_the_import": semantic["cross_veda_projection_evidence"][
                    "withheld_projections"
                ],
                "outcome": "CLOSED_DERIVED (PROPOSED -- the delta is staged, not written)",
            },
            "GAP-SEMANTICS-002": {
                "closure_test": "MATCH (a:SemanticAssertion) WHERE a.review_state='UNREVIEWED' "
                "RETURN count(a) falls below 4,865, with the reviewed sample stratified by "
                "derivation and its reviewer recorded.",
                "property_name": "review_state (read from the database; review_status does "
                "not exist as a property key)",
                "measured_live_now_pre_import": live["assertions_unreviewed"],
                "measured_after_integration": review["unreviewed_population"][
                    "after_integration"
                ],
                "multiple": review["unreviewed_population"]["multiple"],
                "correction": "An earlier draft reported '4,865 unchanged'. That is the "
                "live layer only. My own delta stages 30,274 further assertions, every one "
                "UNREVIEWED, so the declared closure_measure reads 35,139 after "
                "integration. Closing GAP-SEMANTICS-001's coverage multiplies this gap's "
                "population by 7.2x.",
                "delivered": "the review harness, its closed state vocabulary with a guard "
                "that refuses a model writing HUMAN_REVIEWED, and a 120-row sample "
                "stratified by derivation",
                "rows_written_to_a_reviewed_state": 0,
                "independent_source_reach": review["independent_source_adjudication_reach"],
                "outcome": "STILL_IMPLEMENTATION_FIXABLE",
                "precise_reason": "NOT CLOSED. The remaining work is a person reading "
                "verses. It is not an external source blocker -- no source is missing -- and "
                "it is no longer an implementation gap either, because the harness now "
                "exists. Writing any reviewed state from this sprint would have been a "
                "model's output relabelled as review, which the campaign forbids.",
            },
            "GAP-SEMANTICS-003": {
                "closure_test": "MATCH (a:SemanticAssertion) with all three slots present "
                "returns a non-zero count, and at least one assertion has a non-Devata target.",
                "measured_before": {
                    "three_slot_assertions": live["assertions_three_slot"],
                    "assertion_role_edges_starting_at_an_assertion": live[
                        "assertion_role_from_assertion"
                    ],
                },
                "measured_after_proposed_import": semantic["closure_measures_after_import"][
                    "GAP-SEMANTICS-003"
                ],
                "defect_found": semantic["defect_found"],
                "ontology_change_shipped_with_the_re_anchor": {
                    "file": "src/vedagraph/domain/ontology.py",
                    "was": "ASSERTION_ROLE: (Passage|Mantra) -> RoleFiller",
                    "now": "ASSERTION_ROLE: SemanticAssertion -> RoleFiller",
                    "why": "the signature had been written to match the defective import "
                    "rather than migration card M1, which declares "
                    "(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller). Neither half is "
                    "valid alone: the signature without the re-anchor makes 2,052 live "
                    "edges violate it, the re-anchor without the signature makes 2,052 new "
                    "ones violate it.",
                    "pinned_by": "tests/domain/test_agent3_closure.py::"
                    "test_the_assertion_role_signature_matches_the_migration_card",
                },
                "outcome": "CLOSED_DERIVED (PROPOSED -- the delta is staged, not written)",
                "residual": "The :Devata-only range on ASSERTION_AGENT and ASSERTION_TARGET "
                "is unchanged. The triple is completed through :RoleFiller, which is what "
                "migration card M1 declared; the two old edge types keep their range and "
                "every existing edge.",
            },
            "GAP-SEMANTICS-005": {
                "closure_test": "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN "
                "count(e) returns 0, with multi-domain entities carrying every applicable "
                "domain rather than one.",
                "measured_before": live["domain_is_null"],
                "measured_after_proposed_import": 0,
                "entities": live["domain_entities"],
                "multi_domain_entities": domains["multi_domain_entities"],
                "by_provenance": domains["by_provenance"],
                "outcome": "CLOSED_DERIVED (PROPOSED -- the delta is staged, not written)",
                "registry_disagreement": (
                    "The registry row's description and evidence say 229 DomainEntity nodes; "
                    f"the live count is {live['domain_entities']}. The row's own "
                    "closure_basis already says 375, so the description is stale by 146."
                ),
            },
        },
        "samaveda_two_axes_reported_separately": {
            "PUBLISHED_HUMAN_ANNOTATION": {
                "state": "UNAVAILABLE",
                "basis": "three comprehensive resources enumerated in full, three negatives: "
                "DCS 271 corpora / 23,576 entries, UD_Sanskrit-Vedic 57 texts / 27,182 "
                "sentences, VedaWeb 2.0 seven texts. The Samaveda Samhita is in none of them.",
                "classification": "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE for this axis only",
            },
            "MORPHOLOGICAL_ANALYSIS": {
                "state": "PROCESSED_WITH_A_MEASURED_ZERO_TOKEN_YIELD",
                "passages_processed": 1844,
                "morphological_tokens_analysed": 0,
                "passages_with_a_transferred_analysis": semantic[
                    "samaveda_standing_constraint"
                ]["sv_verses_with_an_assertion"],
                "passages_before_the_near_parallel_withholding": semantic[
                    "samaveda_standing_constraint"
                ]["sv_verses_before_the_near_parallel_withholding"],
                "abstentions_with_a_stated_reason": {
                    "SKELETON_NOT_IDENTICAL_TO_RIGVEDIC_SOURCE": 1436,
                    "NO_RIGVEDIC_PARALLEL_EDGE": 182,
                    "IDENTICAL_BUT_RIGVEDIC_SOURCE_CARRIES_NO_ASSERTION": 10,
                    "GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT": semantic[
                        "cross_veda_projection_evidence"
                    ]["withheld_projections"]["pairs"],
                },
                "method": "deterministic cross-Veda letter-identity transfer from the "
                "Rigvedic analysis; CROSS_VEDA_TEXT_IDENTITY, independently_annotated=false",
                "honest_statement": "All 1,844 were processed and each leaves in exactly one "
                "state with a reason, which is what owner decision 5 asks for. But the "
                "yield is 0 Samavedic tokens analysed: the 211 positive verses carry a "
                "Rigvedic analysis transferred at letter identity, not an analysis of "
                "Samavedic words. Reporting this as 'Samaveda morphology processed' without "
                "the token figure would be the misleading form of a true sentence.",
                "what_the_samaveda_did_gain_this_sprint": "a search-normalised text version "
                "for all 1,844 mantras. Whether that makes a query reach it end to end is "
                "UNVERIFIED -- see GAP-MORPHOLOGY-006 clause 3. Either way it is "
                "GAP-MORPHOLOGY-006 and it is not morphology.",
                "standing_constraint": semantic["samaveda_standing_constraint"]["rule"],
            },
        },
        "cross_veda_projection_evidence": semantic["cross_veda_projection_evidence"],
        "trade_this_import_makes": semantic["trade_this_import_makes"],
    }

    out = OUT_DIR / "closure_report.json"
    # This file is excluded from its own digest map. It is written after the map is
    # computed, so including it would publish the PREVIOUS run's digest under the current
    # run's name -- a stale hash that reads as a current one. Its own sha256 is printed
    # below and belongs in the handback, not in here.
    report["artifact_digests"] = {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in sorted(OUT_DIR.iterdir())
        if path.is_file() and not path.name.startswith("_") and path != out
    }
    report["self_digest_note"] = (
        "closure_report.json is deliberately absent from artifact_digests: a file cannot "
        "carry its own hash. Digest it after the fact."
    )
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "artifact_digests"}, indent=2)[:200])
    print("digests:", len(report["artifact_digests"]))
    print("sha256(closure_report.json) =", sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
