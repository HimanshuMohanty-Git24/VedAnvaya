"""Assert the contracts the product graph is allowed to be trusted on.

**Why a script and not only tests.** The pytest suite runs offline by design, so the
invariants that are only observable against a populated database have nowhere to live. Each
check below corresponds to a defect this repository actually shipped at some point, which is
why the checks are phrased as the defect rather than as the desired state:

* an edge with no grade, which makes "filter by ``quality_tier`` to exclude model output"
  silently incomplete;
* a diagnostic node reachable by following edges outward from a product node, which puts
  engineering artifacts in a researcher's result set;
* a ``Work`` with no machine-readable scope, which let a corpus that is the Kauthuma ārcika
  answer to the name "Samaveda Samhita";
* a ``FormulaFamily`` that cannot be traversed to its own members;
* a ``SemanticAssertion`` whose predicate is a property rather than an edge, so
  predicate-level traversal sees only part of the layer;
* a counts block that disagrees with the rows it summarises -- this graph once recorded nine
  corrections of which one had been written;
* rows sent that never landed, the quiet-failure shape every loader here reports separately.

Exit code is 0 only when every FAIL-severity check passes. ``--json`` prints the machine
readable form for a report table.

Usage::

    python scripts/check_live_invariants.py
    python scripts/check_live_invariants.py --json
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import warnings
from dataclasses import dataclass
from typing import Any

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

BOLT_URI = "bolt://localhost:7687"
BOLT_AUTH = ("neo4j", "vedagraph_dev")


@dataclass(frozen=True)
class Invariant:
    """One contract, stated as the count that must be zero (or must equal ``expect``)."""

    name: str
    #: What a non-conforming row means, in the words of the defect it would be.
    defect: str
    cypher: str
    #: FAIL blocks the exit code; WARN is reported and does not.
    severity: str = "FAIL"
    expect: int = 0


INVARIANTS: tuple[Invariant, ...] = (
    Invariant(
        "ungraded_edges",
        "edges carrying no quality_tier, so a tier filter silently misses them",
        "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(r) AS c",
    ),
    Invariant(
        "edges_without_grade_basis",
        "edges that cannot say why they carry the grade they carry",
        "MATCH ()-[r]->() WHERE r.grade_basis IS NULL RETURN count(r) AS c",
    ),
    # The check below is deliberately narrower than "no product node reaches an
    # :Internal node", and the reason is a distinction the `Internal` label does not
    # itself draw. `Internal` marks TWO different kinds of node: the DIAGNOSTIC layer
    # (QAIssue -- facts about this repository, which no researcher should ever traverse
    # into) and SUB-ENTITIES that are not product entities in their own right
    # (TextVersion, Translation, Lemma, Source, SourceArtifact). The second kind MUST stay
    # reachable: a Passage that could not reach its own text or its own translation would
    # be useless. Measured, the broad form of this check reports 70,559 "leaks" --
    # 44,276 HAS_TEXT_VERSION + 17,283 HAS_TRANSLATION + 9,000 MENTIONS_LEMMA -- every one
    # of them legitimate. An auditor running the broad form would report a false CRITICAL,
    # so the invariant names the diagnostic labels instead of the marker label.
    Invariant(
        "product_node_reaching_diagnostic_outward",
        "a product node with an outgoing edge into the diagnostic layer, so normal "
        "outward traversal lands in engineering artifacts (adversarial finding M-2)",
        "MATCH (p)-[r]->(q:QAIssue) WHERE NOT p:Internal RETURN count(r) AS c",
    ),
    Invariant(
        "diagnostic_nodes_not_marked_internal",
        "a diagnostic node that no product filter can exclude, because the one place "
        "the boundary is written down does not cover it",
        "MATCH (q:QAIssue) WHERE NOT q:Internal RETURN count(q) AS c",
    ),
    Invariant(
        "works_without_scope",
        "a Work that does not say what corpus it covers",
        "MATCH (w:Work) WHERE w.scope IS NULL RETURN count(w) AS c",
    ),
    Invariant(
        "works_without_excluded_corpora",
        "a Work whose exclusions are prose only and cannot be filtered on",
        "MATCH (w:Work) WHERE w.excluded_corpora IS NULL RETURN count(w) AS c",
    ),
    Invariant(
        "formula_families_without_outward_edge",
        "a FormulaFamily that is a dead end: its members cannot be reached from it",
        "MATCH (f:FormulaFamily) WHERE NOT (f)-->(:Formula) RETURN count(f) AS c",
        severity="WARN",
    ),
    Invariant(
        "assertions_without_predicate_edge",
        "a SemanticAssertion whose predicate is data but not an edge, so "
        "predicate-level traversal cannot see it (adversarial finding M-3)",
        "MATCH (a:SemanticAssertion) WHERE NOT (a)-[:ASSERTION_PREDICATE]->() RETURN count(a) AS c",
        severity="WARN",
    ),
    Invariant(
        "mention_edges_without_referent_certainty",
        "a deity mention that cannot say whether it means the god or the noun",
        "MATCH ()-[r:MENTIONS_DEVATA]->() WHERE r.referent_certainty IS NULL RETURN count(r) AS c",
    ),
    Invariant(
        "mention_edges_with_retired_certainty_value",
        "a mention edge still carrying a certainty value the layer no longer mints -- "
        "MERGE alone never forgets a superseded value",
        "MATCH ()-[r:MENTIONS_DEVATA]->() "
        "WHERE NOT r.referent_certainty IN "
        "['DEITY_CERTAIN', 'DEITY_PROBABLE', 'DEITY_AMBIGUOUS'] RETURN count(r) AS c",
    ),
    # V3.2 replaced the passage-scoped check with a whole-graph one, which the note below
    # explains is only now safe to write.
    #
    # The history is the argument. `attribution_precision` is defined over PASSAGES --
    # whether a source named this verse, inherited the claim from its hymn, or the verse
    # names the entity itself -- so on a Formula-to-FormulaFamily edge it was a category
    # error, and an earlier build of that layer really did stamp `TEXTUAL_MENTION` there,
    # making a membership edge claim something about textual attribution. An unscoped check
    # then reported 4,074 and an integrator "fixed" it by setting PER_PASSAGE on both
    # formula twins -- which the next reproducible projection correctly reverted, because
    # the loader is the source of truth and the loader had reasoned its way to REMOVING the
    # property. The check was wrong, not the graph.
    #
    # The lesson recorded at the time was: an invariant asserting that EVERY edge carries a
    # property must first be able to say what the property means on every edge. That was
    # right, and V3.2 satisfies it rather than repealing it. AttributionPrecision now has a
    # NOT_AN_ATTRIBUTION member and ATTRIBUTION_CONTRACT says what the property means on all
    # 65 relationship types, so the universal form is finally a true universal.
    #
    # Scoping to passage-touching edges was itself never sound: CONTAINS, HAS_TEXT_VERSION
    # and QA_ISSUE_ON all touch a Passage and none of them attributes anything to it, so the
    # old check demanded a value from 84,000-odd edges that had no business holding one, and
    # got PER_PASSAGE.
    Invariant(
        "edges_without_attribution_precision",
        "an edge that does not say whether it is per-verse, container-inherited, a "
        "textual mention, or not an attribution at all -- a NULL is now unambiguously a "
        "bug, because every relationship type has a declared answer",
        "MATCH ()-[r]->() WHERE r.attribution_precision IS NULL RETURN count(r) AS c",
    ),
    # The check whose absence let REGISTRY_STATED sit on 6 EPITHET_VARIANT_OF edges through
    # three adversarial passes: nothing anywhere enforced that the stored value was a member
    # of the enum, so an undeclared string was indistinguishable from a declared one.
    Invariant(
        "attribution_precision_outside_the_declared_enum",
        "an edge whose attribution_precision is not a member of AttributionPrecision -- "
        "an undeclared value no consumer can filter on and no reader can interpret",
        "MATCH ()-[r]->() WHERE r.attribution_precision IS NOT NULL AND NOT "
        "r.attribution_precision IN ['PER_PASSAGE', 'CONTAINER_INHERITED', "
        "'TEXTUAL_MENTION', 'NOT_AN_ATTRIBUTION'] RETURN count(r) AS c",
    ),
    # Endpoint-level truth, checked independently of the contract table so that the table
    # cannot certify itself. If a relationship carries a real attribution value, one of its
    # endpoints must be a Passage -- otherwise the edge is claiming something about a verse
    # it does not touch. This is the invariant that would have caught BELONGS_TO_FAMILY
    # asserting CONTAINER_INHERITED between a Rishi and a RishiFamily.
    Invariant(
        "attribution_claimed_on_an_edge_with_no_passage",
        "an edge asserting a per-verse, inherited or textual-mention attribution when "
        "neither endpoint is a Passage, so there is no verse for it to be precise about",
        "MATCH (a)-[r]->(b) WHERE NOT (a:Passage OR b:Passage) AND "
        "r.attribution_precision IN ['PER_PASSAGE', 'CONTAINER_INHERITED', "
        "'TEXTUAL_MENTION'] RETURN count(r) AS c",
    ),
    Invariant(
        "family_member_count_disagrees_with_edges",
        "a FormulaFamily whose recorded member_count disagrees with the memberships "
        "that actually landed -- read the rows, not the counts block",
        "MATCH (f:FormulaFamily) "
        "OPTIONAL MATCH (m:Formula)-[:MEMBER_OF_FAMILY]->(f) "
        "WITH f, count(m) AS actual "
        "WHERE f.member_count IS NOT NULL AND f.member_count <> actual "
        "RETURN count(f) AS c",
        severity="WARN",
    ),
    # WARN, not FAIL, and deliberately so: this one is currently non-zero and is reported
    # as a known state rather than hidden. Four predicates carry a SINGLE `confidence`
    # value across every one of their edges (HAS_RISHI 17,889, HAS_CHANDAS 16,331,
    # HAS_DEVATA 10,558, HAS_DEVATA_ASCRIPTION 5,385 -- 50,163 edges at exactly 1.0), so
    # for them the field carries no information whatsoever. It is named `confidence` and
    # is a pipeline prior. Calibration is HUMAN_BLOCKED; the honest containment is the
    # named query `confidence_is_a_pipeline_constant`, which returns this guard per row.
    Invariant(
        "predicates_whose_confidence_is_a_single_constant",
        "a predicate on which `confidence` takes exactly one value, so filtering on it "
        "selects a pipeline branch while looking like it raises precision",
        "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
        "WITH type(r) AS t, count(DISTINCT r.confidence) AS values "
        "WHERE values = 1 RETURN count(t) AS c",
        severity="WARN",
    ),
    # Adversarial finding F-7, generalised. 1,468 ABOUT_CONCEPT edges sat under a second
    # `run_id` whose output no committed artifact asserted -- 0 of their 1,468
    # (passage, concept) pairs appeared in concept_assertions.jsonl, which declares exactly
    # one run. Their grades were good, so no tier or evidence check could see them; the
    # only visible symptom was two run_ids where the artifact declares one. That is
    # unreproducible graph state, the specific failure the V3 projection script exists to
    # prevent, and it was invisible to every check that existed. This invariant is the
    # generalisation: for a layer built by one artifact run, more than one live run_id
    # means either a superseded run was never swept or the artifact is not the source of
    # truth. Both are worth failing on.
    Invariant(
        "predicates_carrying_more_than_one_run_id",
        "a single-run layer with edges from more than one run, so part of the graph is "
        "reproducible from no committed artifact",
        "MATCH ()-[r]->() WHERE r.run_id IS NOT NULL "
        "WITH type(r) AS t, count(DISTINCT r.run_id) AS runs "
        "WHERE runs > 1 AND NOT t IN ['SHARES_ENTITY_VOCABULARY_WITH'] "
        "RETURN count(t) AS c",
    ),
    Invariant(
        "unlabelled_nodes",
        "a node with no label at all, which no product filter can reach or exclude",
        "MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS c",
    ),
    Invariant(
        "passages_without_canonical_citation",
        "a passage a reader cannot cite",
        "MATCH (p:Passage) WHERE p.canonical_citation IS NULL RETURN count(p) AS c",
    ),
    Invariant(
        "devatas_without_display_label",
        "a deity with no readable name",
        "MATCH (d:Devata) WHERE d.display_label IS NULL RETURN count(d) AS c",
    ),
    Invariant(
        "rishi_family_membership_without_evidence",
        "a family membership that cannot say which source string licensed it -- family "
        "must never be assigned from name resemblance",
        "MATCH (r:Rishi)-[m:BELONGS_TO_FAMILY]->(:RishiFamily) "
        "WHERE m.grade_basis IS NULL OR m.evidence IS NULL RETURN count(m) AS c",
    ),
)


def _count(session: Any, cypher: str) -> int:
    record = session.run(cypher).single()
    return int(record["c"]) if record else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    from neo4j import GraphDatabase

    results: list[dict[str, Any]] = []
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            size = session.run(
                "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            for inv in INVARIANTS:
                measured = _count(session, inv.cypher)
                results.append(
                    {
                        "name": inv.name,
                        "severity": inv.severity,
                        "measured": measured,
                        "expected": inv.expect,
                        "pass": measured == inv.expect,
                        "defect": inv.defect,
                    }
                )
    finally:
        driver.close()

    failures = [r for r in results if not r["pass"] and r["severity"] == "FAIL"]
    warns = [r for r in results if not r["pass"] and r["severity"] == "WARN"]

    if args.json:
        print(
            json.dumps(
                {
                    "nodes": size["nodes"],
                    "relationships": size["rels"],
                    "results": results,
                    "failures": len(failures),
                    "warnings": len(warns),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"graph: {size['nodes']:,} nodes / {size['rels']:,} relationships\n")
        for r in results:
            mark = "ok  " if r["pass"] else ("FAIL" if r["severity"] == "FAIL" else "warn")
            print(f"{mark}  {r['name']:<46} {r['measured']:>8,}")
            if not r["pass"]:
                print(f"        -> {r['defect']}")
        print(f"\n{len(failures)} failing, {len(warns)} warning, {len(results)} checked")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
