"""Invariants the enriched graph must satisfy, checked offline and against the live store.

Two passes, and the project's own history says both are needed. The offline pass reads the
artifacts and catches malformed rows before they reach a database. The live pass runs
Cypher against the loaded graph and catches the other class of defect entirely: rows that
were well-formed, passed every unit test and type check, and then did not land, because a
``MERGE`` collapsed them or a ``MATCH`` found no endpoint. Three real defects in the
previous graph release were of exactly that kind, and none of them was visible in the
serialized projection.

So the rule this module enforces is: **a count is what the database contains, not what the
loader was handed.** Every live check compares against the artifact it came from, and a
shortfall is a failure rather than a note.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from vedagraph.enrich.guards import (
    MAX_CONCEPT_ASSERTIONS,
    MAX_CONCEPT_NODES,
    MAX_CONCEPTS_PER_PASSAGE,
    MAX_FORMULA_EDGES,
    MAX_FORMULA_NODES,
    MAX_NEAR_PARALLEL_EDGES,
    MAX_NEAR_PARALLELS_PER_MANTRA,
)
from vedagraph.enrich.predicates import (
    CONTROLLED_PREDICATES,
    REFUSED_PREDICATES,
    StructuralPredicate,
)
from vedagraph.enrich.provenance import ACCEPTABLE_WITHOUT_REVIEW, AssertionState, TrustClass
from vedagraph.enrich.surfaces import contains_private_use


@dataclass
class Finding:
    """One invariant violation, with enough detail to act on."""

    check: str
    severity: str
    count: int
    detail: str
    examples: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "count": self.count,
            "detail": self.detail,
            "examples": self.examples[:10],
        }


@dataclass
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    def add(
        self,
        check: str,
        count: int,
        detail: str,
        examples: Sequence[str] = (),
        severity: str = "ERROR",
    ) -> None:
        self.checks_run.append(check)
        if count:
            self.findings.append(
                Finding(check, severity, count, detail, [str(e) for e in examples[:10]])
            )

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks_run": sorted(set(self.checks_run)),
            "error_count": len(self.errors),
            "findings": [f.as_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Offline: the artifacts
# ---------------------------------------------------------------------------


def _rows_missing_evidence(rows: Sequence[dict[str, Any]]) -> list[str]:
    """Rows whose evidence is absent, however the artifact happens to encode it.

    ``Provenance.as_dict`` leaves evidence as a list of maps and
    ``Provenance.as_edge_properties`` encodes it as a JSON string, and both shapes reach a
    validator depending on whether it is reading an artifact or a graph row. Accepting only
    one of them would silently pass every row of the other.
    """
    missing = []
    for row in rows:
        evidence = row.get("evidence")
        empty = (
            evidence is None
            or (isinstance(evidence, list) and not evidence)
            or (isinstance(evidence, str) and evidence.strip() in ("", "[]", "null"))
        )
        if empty:
            missing.append(str(row.get("parallel_id") or row.get("assertion_id") or row))
    return missing


def validate_artifacts(
    parallels: Sequence[dict[str, Any]],
    formulas: Sequence[dict[str, Any]],
    formula_occurrences: Sequence[dict[str, Any]],
    concepts: Sequence[dict[str, Any]],
    concept_assertions: Sequence[dict[str, Any]],
    semantic_candidates: Sequence[dict[str, Any]],
) -> ValidationResult:
    """Check every invariant that can be decided without a database."""
    result = ValidationResult()
    trust_names = {str(t) for t in TrustClass}
    state_names = {str(s) for s in AssertionState}
    concept_ids = {row["concept_id"] for row in concepts}
    formula_ids = {row["formula_id"] for row in formulas}

    # --- controlled vocabulary -------------------------------------------------
    all_predicated = list(parallels) + list(semantic_candidates)
    bad_predicates = [
        f"{row.get('predicate')} on {row.get('parallel_id') or row.get('candidate_id')}"
        for row in all_predicated
        if row.get("predicate") not in CONTROLLED_PREDICATES
    ]
    result.add(
        "controlled_predicates",
        len(bad_predicates),
        "relationship names outside the controlled enrichment vocabulary",
        bad_predicates,
    )

    refused_used = [
        str(row.get("predicate"))
        for row in all_predicated
        if str(row.get("predicate")) in REFUSED_PREDICATES
    ]
    result.add(
        "refused_predicates_not_emitted",
        len(refused_used),
        "a predicate this layer refuses by name was emitted anyway",
        refused_used,
    )

    # --- trust classes ---------------------------------------------------------
    every_row = (
        list(parallels)
        + list(formulas)
        + list(formula_occurrences)
        + list(concept_assertions)
        + list(semantic_candidates)
    )
    bad_trust = [str(row.get("trust")) for row in every_row if row.get("trust") not in trust_names]
    result.add("trust_class_wellformed", len(bad_trust), "unknown trust class", bad_trust)

    bad_state = [str(row.get("state")) for row in every_row if row.get("state") not in state_names]
    result.add("assertion_state_wellformed", len(bad_state), "unknown assertion state", bad_state)

    accepted_by_model = [
        str(row.get("candidate_id") or row.get("assertion_id"))
        for row in every_row
        if row.get("state") == str(AssertionState.ACCEPTED)
        and row.get("trust") not in {str(t) for t in ACCEPTABLE_WITHOUT_REVIEW}
    ]
    result.add(
        "llm_output_is_never_accepted",
        len(accepted_by_model),
        "a model-extracted row was written as ACCEPTED without human review",
        accepted_by_model,
    )

    model_mismatch = [
        str(row.get("method"))
        for row in every_row
        if (row.get("trust") == str(TrustClass.LLM_EXTRACTED)) != bool(row.get("model"))
    ]
    result.add(
        "model_recorded_for_llm_rows_only",
        len(model_mismatch),
        "LLM_EXTRACTED without a model name, or a model name on a deterministic row",
        model_mismatch,
    )

    # --- evidence --------------------------------------------------------------
    result.add(
        "parallels_carry_evidence",
        len(_rows_missing_evidence(parallels)),
        "textual-parallel rows with no evidence span",
        _rows_missing_evidence(parallels),
    )
    result.add(
        "concept_assertions_carry_evidence",
        len(_rows_missing_evidence(concept_assertions)),
        "concept assertions with no evidence span",
        _rows_missing_evidence(concept_assertions),
    )

    # --- publishable text ------------------------------------------------------
    # Nothing a person reads may contain a private-use code point. This check exists
    # because the release shipped 5,554 parallel rows and 15,229 concept assertions whose
    # evidence carried the comparison fold's U+E000-U+E003 sentinels, and every other check
    # in this module passed while it did: an unassigned code point usually renders as
    # nothing, so the corruption was invisible and the quotes still looked like Sanskrit.
    leaked: list[str] = []
    for row in every_row:
        spans = row.get("evidence")
        texts = [row.get("notes", "")]
        if isinstance(spans, list):
            texts += [str(span.get("quote", "")) for span in spans if isinstance(span, dict)]
        elif isinstance(spans, str):
            texts.append(spans)
        for field_text in texts:
            if contains_private_use(str(field_text)):
                row_id = (
                    row.get("parallel_id") or row.get("assertion_id") or row.get("candidate_id")
                )
                leaked.append(f"{row_id}: {field_text[:60]}")
                break
    result.add(
        "published_text_is_free_of_private_use_code_points",
        len(leaked),
        "evidence or notes containing an unassigned code point from the comparison fold",
        leaked,
    )

    for name, rows_ in (("formulas", formulas), ("concepts", concepts)):
        bad_display = [
            str(row.get("display_form") or row.get("preferred_label_sa", ""))
            for row in rows_
            if contains_private_use(
                str(row.get("display_form") or row.get("preferred_label_sa", ""))
            )
        ]
        result.add(
            f"{name}_display_form_is_printable",
            len(bad_display),
            "a display string containing an unassigned code point",
            bad_display,
        )

    # --- referential integrity -------------------------------------------------
    dangling_concepts = [
        str(row.get("concept_id"))
        for row in concept_assertions
        if row.get("concept_id") not in concept_ids
    ]
    result.add(
        "concept_assertions_resolve",
        len(dangling_concepts),
        "concept assertion naming a concept that does not exist",
        dangling_concepts,
    )

    dangling_formulas = [
        str(row.get("formula_id"))
        for row in formula_occurrences
        if row.get("formula_id") not in formula_ids
    ]
    result.add(
        "formula_occurrences_resolve",
        len(dangling_formulas),
        "formula occurrence naming a formula that does not exist",
        dangling_formulas,
    )

    # --- identity --------------------------------------------------------------
    for name, rows, key in (
        ("concept_ids_unique", concepts, "concept_id"),
        ("formula_ids_unique", formulas, "formula_id"),
        ("parallel_ids_unique", parallels, "parallel_id"),
        ("concept_assertion_ids_unique", concept_assertions, "assertion_id"),
        ("semantic_candidate_ids_unique", semantic_candidates, "candidate_id"),
    ):
        counts = Counter(str(row.get(key)) for row in rows)
        dupes = [value for value, count in counts.items() if count > 1]
        result.add(name, len(dupes), f"duplicate {key}", dupes)

    # --- cross-Veda identity ---------------------------------------------------
    self_pairs = [
        f"{row.get('subject_key')} -> {row.get('object_key')}"
        for row in parallels
        if row.get("subject_key") == row.get("object_key")
        or row.get("subject_veda") == row.get("object_veda")
    ]
    result.add(
        "cross_veda_pairs_span_two_vedas",
        len(self_pairs),
        "a cross-Veda parallel whose two sides are the same passage or the same Veda",
        self_pairs,
    )

    # --- explosion guards ------------------------------------------------------
    near = [row for row in parallels if row.get("predicate") == "NEAR_PARALLEL_OF"]
    result.add(
        "near_parallel_edge_cap",
        max(0, len(near) - MAX_NEAR_PARALLEL_EDGES),
        f"near-parallel edges exceed the {MAX_NEAR_PARALLEL_EDGES} circuit breaker",
    )

    per_mantra: Counter[tuple[str, str]] = Counter()
    for row in near:
        per_mantra[(str(row.get("subject_key")), str(row.get("object_veda")))] += 1
        per_mantra[(str(row.get("object_key")), str(row.get("subject_veda")))] += 1
    over = [
        f"{key} ({count})"
        for key, count in per_mantra.items()
        if count > MAX_NEAR_PARALLELS_PER_MANTRA
    ]
    result.add(
        "near_parallels_per_mantra_cap",
        len(over),
        f"mantras with more than {MAX_NEAR_PARALLELS_PER_MANTRA} near parallels into one Veda",
        over,
    )

    result.add("concept_node_cap", max(0, len(concepts) - MAX_CONCEPT_NODES), "too many concepts")
    result.add(
        "concept_assertion_cap",
        max(0, len(concept_assertions) - MAX_CONCEPT_ASSERTIONS),
        "too many concept assertions",
    )
    result.add("formula_node_cap", max(0, len(formulas) - MAX_FORMULA_NODES), "too many formulas")
    result.add(
        "formula_edge_cap",
        max(0, len(formula_occurrences) - MAX_FORMULA_EDGES),
        "too many formula occurrence edges",
    )

    per_passage: Counter[str] = Counter(str(row.get("passage_key")) for row in concept_assertions)
    over_concept = [
        f"{key} ({n})" for key, n in per_passage.items() if n > MAX_CONCEPTS_PER_PASSAGE
    ]
    result.add(
        "concepts_per_passage_cap",
        len(over_concept),
        f"passages with more than {MAX_CONCEPTS_PER_PASSAGE} concepts",
        over_concept,
    )

    return result


# ---------------------------------------------------------------------------
# Live: the database
# ---------------------------------------------------------------------------

#: Every relationship type the enrichment layer may write, derived from the controlled
#: vocabulary rather than restated.
#:
#: It was a hand-written list once, and the omission it caused is worth recording. The
#: fourteen semantic predicates were missing from it, so ``validate_live`` fell through to
#: its node-count branch and ran ``MATCH (n:DESCRIBES)`` -- which is zero, because
#: ``DESCRIBES`` is a relationship type and not a label. The check then reported "wrote
#: 280, database holds 0" for 736 edges that had in fact loaded correctly. A validator that
#: cries wolf is worse than one check short: it teaches the reader to skim past the one
#: time it is right. Deriving the tuple means a new predicate cannot be forgotten here.
#:
#: ``QA_ISSUE_ON`` is excluded because it is a corpus projection rather than an enrichment
#: assertion and carries no provenance envelope.
_ENRICHMENT_TYPES: tuple[str, ...] = tuple(
    sorted(CONTROLLED_PREDICATES - {str(StructuralPredicate.QA_ISSUE_ON)})
)


def validate_live(session: Any, expected: dict[str, int]) -> ValidationResult:
    """Run the invariants that only a loaded graph can answer.

    ``expected`` maps a relationship type or label to the number of rows the build wrote,
    so a shortfall between artifact and database is reported as a defect rather than
    discovered later as a puzzling count.
    """
    result = ValidationResult()

    def scalar(cypher: str, **params: Any) -> int:
        record = session.run(cypher, **params).single()
        return int(record[0]) if record else 0

    # --- what landed vs what was sent -----------------------------------------
    shortfalls = []
    for name, sent in sorted(expected.items()):
        if name in _ENRICHMENT_TYPES:
            landed = scalar(
                f"MATCH ()-[r:{name}]->() WHERE r.pipeline_version IS NOT NULL RETURN count(r)"
            )
        else:
            landed = scalar(f"MATCH (n:{name}) RETURN count(n)")
        if landed != sent:
            shortfalls.append(f"{name}: wrote {sent}, database holds {landed}")
    result.add(
        "every_written_row_landed",
        len(shortfalls),
        "artifact row count does not match the database",
        shortfalls,
    )

    # --- orphans ---------------------------------------------------------------
    orphan_concepts = scalar(
        "MATCH (c:Concept) WHERE NOT (c)<-[:ABOUT_CONCEPT]-() AND NOT (c)-[:BROADER_THAN]-() "
        "AND NOT (c)<-[:DEVATA_ASSOCIATED_WITH]-() RETURN count(c)"
    )
    result.add(
        "no_unreferenced_concepts",
        orphan_concepts,
        "Concept nodes nothing points at",
        severity="WARNING",
    )

    orphan_formulas = scalar("MATCH (f:Formula) WHERE NOT (f)<-[:USES_FORMULA]-() RETURN count(f)")
    result.add("no_orphan_formulas", orphan_formulas, "Formula nodes with no occurrence")

    # --- evidence on every enrichment edge -------------------------------------
    for rel_type in _ENRICHMENT_TYPES:
        missing = scalar(
            f"MATCH ()-[r:{rel_type}]->() "
            "WHERE r.pipeline_version IS NOT NULL AND (r.evidence IS NULL OR r.evidence = '[]') "
            "RETURN count(r)"
        )
        result.add(
            "enrichment_edges_carry_evidence",
            missing,
            f"{rel_type} edges with no evidence",
        )

    # --- trust classes in the database -----------------------------------------
    known = {str(t) for t in TrustClass}
    bad = []
    for rel_type in _ENRICHMENT_TYPES:
        for record in session.run(
            f"MATCH ()-[r:{rel_type}]->() WHERE r.pipeline_version IS NOT NULL "
            "RETURN DISTINCT r.trust AS trust"
        ):
            if record["trust"] not in known:
                bad.append(f"{rel_type}: {record['trust']!r}")
    result.add("live_trust_classes_wellformed", len(bad), "unknown trust class in the graph", bad)

    # --- concept assertions resolve --------------------------------------------
    dangling = scalar("MATCH ()-[r:ABOUT_CONCEPT]->(c) WHERE NOT c:Concept RETURN count(r)")
    result.add(
        "live_concept_assertions_resolve", dangling, "ABOUT_CONCEPT not pointing at a Concept"
    )

    # --- duplicate canonical identity ------------------------------------------
    for label, key in (
        ("Passage", "canonical_key"),
        ("Concept", "concept_id"),
        ("Formula", "formula_id"),
        ("Translation", "translation_id"),
    ):
        dupes = scalar(
            f"MATCH (n:{label}) WITH n.{key} AS k, count(*) AS c WHERE c > 1 RETURN count(*)"
        )
        result.add(f"{label.lower()}_identity_unique", dupes, f"duplicate {label}.{key}")

    # --- cross-Veda edges really span two Vedas --------------------------------
    same_veda = scalar(
        "MATCH (a:Passage)-[r]->(b:Passage) "
        "WHERE r.pipeline_version IS NOT NULL AND a.veda = b.veda RETURN count(r)"
    )
    result.add(
        "live_cross_veda_edges_span_two_vedas",
        same_veda,
        "an enrichment parallel edge whose endpoints are in the same Veda",
    )

    # --- no enrichment edge dangles into a non-existent node -------------------
    self_loops = scalar("MATCH (a)-[r]->(a) WHERE r.pipeline_version IS NOT NULL RETURN count(r)")
    result.add("no_enrichment_self_loops", self_loops, "an enrichment edge from a node to itself")

    return result
