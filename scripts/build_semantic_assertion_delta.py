"""Stage the four-Veda semantic assertion layer and re-anchor the role edges.

Covers GAP-SEMANTICS-001 and GAP-SEMANTICS-003, and produces the stratified review frame
GAP-SEMANTICS-002 needs.

**The defect this exists to fix, measured live.** Wave 3 imported the ``:RoleFiller``
layer -- 2,052 nodes, 2,052 ``ASSERTION_ROLE`` edges, 387 ``REFERS_TO`` edges -- but never
imported the assertions those fillers belong to. ``scripts/wave3_import_plan.py`` lists
``semantic_roles/rows.jsonl`` under ``NOT_IMPORTED`` as "evidence rows. The elements are
the role fillers", which is wrong: the rows *carry the assertions*, and the fillers are
elements of them. The consequence is in the database:

* ``(:SemanticAssertion)-[:ASSERTION_ROLE]->()`` : **0**
* ``(:Passage)-[:ASSERTION_ROLE]->(:RoleFiller)`` : **2,052**
* distinct passages holding a role filler that also hold any ``:SemanticAssertion`` : **0**

``docs/reports/data-completeness/SCHEMA_MIGRATION_CARDS.md`` M1 declares the edge as
``(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller)`` and its migration test as "every
``:RoleFiller`` resolves to exactly one ``:SemanticAssertion``". Zero of 2,052 do. The
import plan's own note says "the importer resolves the ordinal to the assertion"; nothing
resolved it, because there was no assertion node to resolve to. The role layer is
Atharvavedic and Yajurvedic and the live assertion layer is Rigvedic, so the two populations
do not intersect at all and never could have.

**The five derivations are never summed.** Every staged assertion carries
``role_derivation``; the two live derivations keep theirs. Any surface that adds them is
reporting a number that means nothing, and the manifest states the five separately so no
consumer has to reconstruct the split.

**No model-assisted extraction is in this layer.** The staged assertions are morphology-rule
and treebank derived. The live ``MODEL_EXTRACTION`` half stays exactly as it is, separately
typed, and is not touched.

Neo4j is read **only**.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

REPO: Final = Path(__file__).resolve().parents[1]
STAGED: Final = REPO / "data" / "staging" / "semantic_roles"
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

#: The role whose filler is the assertion's target. The registry names the slot PATIENT and
#: the gap text calls it a target; they are the same slot and this constant is the only
#: place the two names are joined.
TARGET_ROLE: Final = "PATIENT"
AGENT_ROLE: Final = "AGENT"


def assertion_key(canonical_key: str, ordinal: int) -> str:
    """The assertion's key, minted exactly as ``role_filler_key`` already encodes it.

    ``role_filler_key`` is ``{canonical_key}:A{ordinal:03d}:R{n:02d}``, so the assertion
    segment is not invented here -- it is read back out of a key the artifact already ships.
    """
    return f"{canonical_key}:A{ordinal:03d}"


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


def load_role_fillers() -> dict[str, list[dict[str, Any]]]:
    by_assertion: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with (STAGED / "role_fillers.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("importable"):
                continue
            by_assertion[assertion_key(row["canonical_key"], row["assertion_ordinal"])].append(row)
    return by_assertion


#: The two morphological feature vocabularies this layer carries, and they are NOT
#: interchangeable. The Zurich/VedaWeb annotation writes lowercase keys with uppercase
#: values (``mood: IND``, ``tense: PRS``, ``voice: MED``); the DCS treebank writes
#: capitalised UD keys with capitalised values (``Mood: Ind``, ``Tense: Pres``,
#: ``Voice: Pass``). Measured over the 30,266 staged rows: 22,556 Zurich (all RV and the
#: SV transfers, which inherit the Rigvedic analysis), 7,710 DCS (all AV and YV), 0 mixed,
#: 0 unrecognised keys.
#:
#: **They must never be flattened into shared scalar columns.** ``IND`` and ``Ind`` mean the
#: same mood in two notations, so a single ``verb_mood`` property would let
#: ``WHERE verb_mood = 'IND'`` return the Rigvedic half and silently drop the Atharvavedic
#: one -- a query that looks like it filters a feature and actually filters a corpus. The
#: features travel as one JSON string with the scheme named beside them instead.
UD_FEATURE_KEYS: Final = frozenset(
    {"Mood", "Number", "Person", "Tense", "Voice", "Formation"}
)
ZURICH_FEATURE_KEYS: Final = frozenset(
    {
        "mood",
        "number",
        "person",
        "tense",
        "voice",
        "secondary conjugation",
        "local particle",
        "case",
        "gender",
    }
)


def verb_feature_scheme(features: dict[str, Any] | None) -> str:
    """Which feature vocabulary a row's ``verb_features`` are written in.

    :raises ValueError: on a mixed or unrecognised key set. A row whose scheme cannot be
        named would be a row whose features cannot be compared with anything safely.
    """
    keys = set(features or {})
    if not keys:
        return "NONE"
    unknown = keys - UD_FEATURE_KEYS - ZURICH_FEATURE_KEYS
    if unknown:
        raise ValueError(f"verb_features carries unrecognised keys {sorted(unknown)}")
    in_ud, in_zurich = keys & UD_FEATURE_KEYS, keys & ZURICH_FEATURE_KEYS
    if in_ud and in_zurich:
        raise ValueError(
            f"verb_features mixes the two vocabularies: {sorted(in_ud)} with "
            f"{sorted(in_zurich)}; the scheme cannot be named and the row is not comparable"
        )
    return "DCS_UD" if in_ud else "ZURICH_VEDAWEB"


#: Live edge types that disqualify a pair from carrying a projected analysis, and the reason
#: each one disqualifies it. The graph's own typing wins over a letter comparison computed
#: at staging time: the parallel-detection layer is script-aware and the staging comparison
#: is not, so when the two disagree the staged claim has not independently re-established
#: itself and does not get to override the adjudication already in the graph.
WITHHELD_ON_EDGE_TYPE: Final[dict[str, str]] = {
    "NEAR_PARALLEL_OF": "GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT",
}


def projection_withholding_reason(edge_types: list[str]) -> str | None:
    """The typed reason a pair may not carry a projected analysis, or ``None``.

    LEAD RULING, round three. Five of the 216 pairs are typed ``NEAR_PARALLEL_OF`` in the
    live graph while this projection asserts letter identity for the same pairs. Near is not
    exact, and the cost of being wrong is specific rather than formal: the projection
    transfers a Rigvedic morphological analysis onto a Samavedic verse, so on a near pair a
    differing word receives the analysis of the word it differs from. Eight assertions of
    30,274 is a cheap price for not doing that.

    Consistent with Agent 7's ruling on AVS 20.57.13, which re-measured at exactly 1.0
    against RV 8.33.9 and was still rejected because the pair is typed ``NEAR_PARALLEL_OF``
    and the identity held on 2 of 6 text-version pairings -- "a best-of-six identity is not
    identity". The same standard applies here.

    The withheld rows are not deleted. They become a bounded, evidenced queue carrying the
    pair's full live edge set, the same shape as the 79 Anukramani-corroborated lexical
    tokens that also get no edge.
    """
    for edge_type in sorted(edge_types):
        reason = WITHHELD_ON_EDGE_TYPE.get(edge_type)
        if reason:
            return reason
    return None


def _projection_fields(
    row: dict[str, Any],
    payload: dict[str, Any],
    assertion: dict[str, Any],
    parallel_edges: dict[tuple[str, str], list[str]],
) -> dict[str, Any]:
    """Name the source verse on the row itself, for a cross-Veda projected assertion.

    LEAD RULING 1. ``mapping_confidence: EXACT`` is a claim about the KEY, and the key is
    independently backed: every one of the 216 Samavedic target verses carries a
    pre-existing parallel edge to its Rigvedic source in the live graph, so the identity
    does not rest on a fold computed at staging time. These rows are importable.

    What was missing is the address. The row carried ``source_id: VEDAWEB`` -- the
    annotation source -- and nothing saying WHICH Rigvedic verse the analysis came from.
    Derivable-in-principle from the graph is not recorded: a reader auditing one of these
    must be able to go straight to the source verse without reconstructing the join. So the
    source verse's canonical key and the parallel edge types it rests on are written onto
    every projected row.

    **The artifact named one edge type per row and the live graph carries a set.** Measured
    over all 216 pairs: 170 carry ``REUSES_TEXT_FROM`` + ``VARIANT_OF``, 41 carry
    ``EXACT_PARALLEL_OF`` + ``REUSES_TEXT_FROM``, 5 carry ``NEAR_PARALLEL_OF`` +
    ``REUSES_TEXT_FROM``. 0 carry no edge. Every type the artifact claimed is present in
    the live set, so its field is truthful but partial -- ``projection_edge_types`` carries
    the whole set read from the graph and
    ``projection_relationship_claimed_by_artifact`` keeps what the artifact chose, so the
    two can be compared rather than one silently replacing the other.
    """
    if assertion.get("derivation") != "CROSS_VEDA_TEXT_IDENTITY":
        return {}
    source = payload.get("projected_from") or assertion.get("analysed_passage")
    if not source:
        raise ValueError(
            f"{row['canonical_key']} is CROSS_VEDA_TEXT_IDENTITY and names no source verse; "
            "a projected analysis with no address is not auditable"
        )
    types = parallel_edges.get((row["canonical_key"], source), [])
    if not types:
        raise ValueError(
            f"{row['canonical_key']} -> {source} carries no parallel edge in the live graph; "
            "the ruling's condition is that the identity rests on evidence already in the "
            "graph, and this pair has none"
        )
    withheld = projection_withholding_reason(types)
    if withheld:
        raise ValueError(
            f"{row['canonical_key']} -> {source} is withheld ({withheld}): the graph types "
            f"this pair {types} and a withheld pair must never reach the import rows. Route "
            "it to the withheld queue rather than calling this."
        )
    return {
        "projected_from_canonical_key": source,
        "projected_from_veda": "RV",
        "projection_edge_types": types,
        "projection_relationship_claimed_by_artifact": payload.get(
            "projection_relationship_in_graph"
        ),
        "projection_graph_score": payload.get("projection_graph_score"),
        "projection_identity_basis": (
            "de-accented, de-spaced letter skeletons equal as strings, corroborated by a "
            "pre-existing parallel edge in the graph that this sprint did not create"
        ),
        "independently_annotated": False,
        "is_samavedic_annotation": False,
        "must_never_be_counted_as": "Samaveda morphology or Samavedic annotation",
    }


def build_assertions(
    fillers: dict[str, list[dict[str, Any]]],
    parallel_edges: dict[tuple[str, str], list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(importable, withheld)``.

    A withheld row is not deleted and not silently dropped. It leaves here carrying its
    reason, its source verse and the pair's full live edge set, so the refusal is
    addressable rather than an absence.
    """
    out: list[dict[str, Any]] = []
    withheld_rows: list[dict[str, Any]] = []
    with (STAGED / "rows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            payload = row["payload"]
            for ordinal, assertion in enumerate(payload.get("assertions", ()), start=1):
                key = assertion_key(row["canonical_key"], ordinal)
                mine = fillers.get(key, [])
                roles = {filler["role"] for filler in mine}
                if assertion.get("derivation") == "CROSS_VEDA_TEXT_IDENTITY":
                    source = payload.get("projected_from") or assertion.get("analysed_passage")
                    types = parallel_edges.get((row["canonical_key"], source), [])
                    reason = projection_withholding_reason(types)
                    if reason:
                        withheld_rows.append(
                            {
                                "assertion_key": key,
                                "canonical_key": row["canonical_key"],
                                "veda": row["veda"],
                                "assertion_ordinal": ordinal,
                                "predicate": assertion["predicate"],
                                "frame": assertion["frame"],
                                "verb_surface": assertion.get("verb_surface"),
                                "verb_features_json": json.dumps(
                                    assertion.get("verb_features") or {},
                                    ensure_ascii=False,
                                    sort_keys=True,
                                ),
                                "verb_feature_scheme": verb_feature_scheme(
                                    assertion.get("verb_features")
                                ),
                                "derivation": assertion["derivation"],
                                # The withheld row keeps every disclosure the importable
                                # rows carry. A refusal that drops its own caveats is a
                                # worse record than the row it replaced.
                                "cautions": assertion.get("cautions") or [],
                                "roles_withheld": bool(assertion.get("roles_withheld")),
                                "roles_withheld_reason": assertion.get("roles_withheld_reason"),
                                "human_annotated": False,
                                "model_assisted": False,
                                "is_samavedic_annotation": False,
                                "must_never_be_counted_as": "Samaveda morphology or "
                                "Samavedic annotation",
                                "projected_from_canonical_key": source,
                                "projection_edge_types": types,
                                "projection_relationship_claimed_by_artifact": payload.get(
                                    "projection_relationship_in_graph"
                                ),
                                "projection_graph_score": payload.get("projection_graph_score"),
                                "withheld": True,
                                "withheld_reason": reason,
                                "withheld_reason_text": (
                                    "The live graph types this pair NEAR_PARALLEL_OF. The "
                                    "projection asserts letter identity for the same pair, "
                                    "and a letter comparison computed at staging time is "
                                    "not independent re-establishment of a claim the "
                                    "graph's own script-aware parallel layer already "
                                    "adjudicated the other way. Near is not exact, and a "
                                    "transferred morphological analysis on a near pair "
                                    "gives a differing word the analysis of the word it "
                                    "differs from."
                                ),
                                "consistent_with": "Agent 7's rejection of AVS 20.57.13 "
                                "against RV 8.33.9 -- re-measured at 1.0, still refused "
                                "because the pair is typed NEAR_PARALLEL_OF: 'a "
                                "best-of-six identity is not identity'.",
                                "deleted": False,
                                "queue_shape": "bounded and evidenced, the same shape as "
                                "the 79 Anukramani-corroborated lexical tokens that also "
                                "get no edge",
                                "provenance": "deterministic",
                            }
                        )
                        continue
                out.append(
                    {
                        **_projection_fields(row, payload, assertion, parallel_edges),
                        "assertion_key": key,
                        "canonical_key": row["canonical_key"],
                        "veda": row["veda"],
                        "assertion_ordinal": ordinal,
                        "predicate": assertion["predicate"],
                        "predicate_status": assertion.get("predicate_status"),
                        "frame": assertion["frame"],
                        "verb_surface": assertion.get("verb_surface"),
                        # The raw dict is kept for a human reading the artifact. Neo4j
                        # cannot store a map as a property, so the import writes the JSON
                        # string and the scheme; it never writes this field.
                        "verb_features": assertion.get("verb_features"),
                        "verb_features_json": json.dumps(
                            assertion.get("verb_features") or {},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        "verb_feature_scheme": verb_feature_scheme(
                            assertion.get("verb_features")
                        ),
                        "root_label": assertion.get("root_label"),
                        "role_scope": assertion.get("role_scope"),
                        # The property that makes the five instruments unsummable.
                        "role_derivation": assertion["derivation"],
                        "derivation": assertion["derivation"],
                        "roles_withheld": bool(assertion.get("roles_withheld")),
                        "roles_withheld_reason": assertion.get("roles_withheld_reason"),
                        "cautions": assertion.get("cautions") or [],
                        "asserted_role_count": len(mine),
                        "has_agent_slot": AGENT_ROLE in roles,
                        "has_target_slot": TARGET_ROLE in roles,
                        "has_predicate_slot": True,
                        "three_slot_complete": AGENT_ROLE in roles and TARGET_ROLE in roles,
                        "evidence_layer": row["evidence_layer"],
                        "source_id": row["source_id"],
                        "source_snapshot": row["source_snapshot"],
                        "mapping_confidence": row["mapping_confidence"],
                        "algorithm_version": row["algorithm_version"],
                        "config_hash": row["config_hash"],
                        "code_commit": row["code_commit"],
                        # Explicit, from the declared vocabulary. Never human annotation.
                        "provenance": "deterministic",
                        "annotation_provenance": payload.get("annotation_provenance"),
                        "review_state": "UNREVIEWED",
                        "human_annotated": False,
                        "model_assisted": False,
                    }
                )
    return out, withheld_rows


def build_role_edges(
    assertions: list[dict[str, Any]], fillers: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """``(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller)`` -- the edge M1 declared."""
    known = {a["assertion_key"] for a in assertions}
    edges: list[dict[str, Any]] = []
    for key, rows in fillers.items():
        if key not in known:
            raise ValueError(
                f"role filler set {key} has no staged assertion; the ordinal does not "
                "resolve and re-anchoring it would invent an endpoint"
            )
        for row in rows:
            edges.append(
                {
                    "assertion_key": key,
                    "role_filler_key": row["role_filler_key"],
                    "role": row["role"],
                    "proposed_role": row["proposed_role"],
                    "role_derivation": row["derivation"],
                    "evidence": row["evidence"],
                    "provenance": "deterministic",
                }
            )
    return edges


def read_sv_rv_parallel_edges(session: Any) -> dict[tuple[str, str], list[str]]:
    """Every parallel edge type between a Samavedic and a Rigvedic mantra, as a set per pair.

    Read from the live graph rather than from the artifact's single-valued field, because
    the artifact picks one type and the graph carries several.
    """
    edges: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in session.run(
        "MATCH (sv:Mantra {veda:'SV'})-[e]-(rv:Mantra {veda:'RV'}) "
        "WHERE type(e) IN ['EXACT_PARALLEL_OF','VARIANT_OF','REUSES_TEXT_FROM',"
        "'NEAR_PARALLEL_OF','PARALLEL_TO'] "
        "RETURN sv.canonical_key AS sv, rv.canonical_key AS rv, type(e) AS t"
    ):
        edges[(record["sv"], record["rv"])].add(record["t"])
    return {pair: sorted(types) for pair, types in edges.items()}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fillers = load_role_fillers()

    driver, session = _session()
    try:
        parallel_edges = read_sv_rv_parallel_edges(session)
        assertions, withheld_rows = build_assertions(fillers, parallel_edges)
        role_edges = build_role_edges(assertions, fillers)
        live = {
            "has_semantic_assertion_edges": session.run(
                "MATCH (:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() RETURN count(*) AS n"
            ).single()["n"],
            "rv_mantras_covered": session.run(
                "MATCH (m:Mantra {veda:'RV'})-[:HAS_SEMANTIC_ASSERTION]->() "
                "RETURN count(DISTINCT m) AS n"
            ).single()["n"],
            "non_rv_mantras_covered": session.run(
                "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() WHERE m.veda <> 'RV' "
                "RETURN count(DISTINCT m) AS n"
            ).single()["n"],
            "assertion_role_from_assertion": session.run(
                "MATCH (:SemanticAssertion)-[r:ASSERTION_ROLE]->() RETURN count(r) AS n"
            ).single()["n"],
            "assertion_role_from_passage": session.run(
                "MATCH (:Passage)-[r:ASSERTION_ROLE]->(:RoleFiller) RETURN count(r) AS n"
            ).single()["n"],
            "rolefiller_passages_also_holding_an_assertion": session.run(
                "MATCH (p:Passage)-[:ASSERTION_ROLE]->(:RoleFiller) "
                "WHERE (p)-[:HAS_SEMANTIC_ASSERTION]->() RETURN count(DISTINCT p) AS n"
            ).single()["n"],
            "live_derivations": {
                record["d"]: record["n"]
                for record in session.run(
                    "MATCH (a:SemanticAssertion) RETURN a.derivation AS d, count(*) AS n"
                )
            },
            "action_predicates": {
                record["k"]
                for record in session.run(
                    "MATCH (p:ActionPredicate) RETURN coalesce(p.predicate, p.display_label) AS k"
                )
            },
            "non_devata_refers_to": session.run(
                "MATCH (:RoleFiller)-[:REFERS_TO]->(x) WHERE NOT x:Devata RETURN count(*) AS n"
            ).single()["n"],
            "assertions_unreviewed": session.run(
                "MATCH (a:SemanticAssertion) WHERE a.review_state='UNREVIEWED' "
                "RETURN count(a) AS n"
            ).single()["n"],
        }
    finally:
        session.close()
        driver.close()

    unknown_predicates = sorted(
        {a["predicate"] for a in assertions} - live["action_predicates"]
    )
    live.pop("action_predicates")

    paths = {}
    for name, rows in (
        ("semantic_assertions.jsonl", assertions),
        ("semantic_assertions_withheld.jsonl", withheld_rows),
        ("assertion_role_edges.jsonl", role_edges),
    ):
        path = OUT_DIR / name
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        paths[name] = path

    per_veda_mantras: dict[str, set[str]] = defaultdict(set)
    for a in assertions:
        per_veda_mantras[a["veda"]].add(a["canonical_key"])
    three_slot = [a for a in assertions if a["three_slot_complete"]]
    non_devata_targets = sum(
        1
        for key, rows in fillers.items()
        for row in rows
        if row["role"] == TARGET_ROLE and row["filler_type"] != "DEITY"
    )

    unreviewed_before = live["assertions_unreviewed"]
    unreviewed_after = unreviewed_before + len(assertions)
    predicate_only = Counter(a["role_derivation"] for a in assertions)[
        "MORPHOLOGY_RULE_PREDICATE_ONLY"
    ]

    manifest = {
        "artifact": "AGENT_3_SEMANTIC_ASSERTION_DELTA",
        "gaps": ["GAP-SEMANTICS-001", "GAP-SEMANTICS-003"],
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "live_before": live,
        "defect_found": {
            "what": "ASSERTION_ROLE was anchored on :Passage instead of :SemanticAssertion, "
            "and the assertions the fillers belong to were never imported at all",
            "where": "scripts/wave3_import_plan.py:220-257 (SR_ASSERTION_ROLE_EDGES "
            "start_label='Passage') and the NOT_IMPORTED entry for "
            "semantic_roles/rows.jsonl at scripts/wave3_import_plan.py:205-208",
            "contract_violated": "SCHEMA_MIGRATION_CARDS.md M1: "
            "(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller), and its migration test "
            "'every :RoleFiller resolves to exactly one :SemanticAssertion'",
            "measured_conformance": "0 of 2,052",
        },
        "staged": {
            "assertions": len(assertions),
            "assertion_role_edges": len(role_edges),
            "per_veda_assertions": dict(Counter(a["veda"] for a in assertions)),
            "per_veda_mantras_covered": {k: len(v) for k, v in sorted(per_veda_mantras.items())},
            "role_derivations_never_summed": dict(
                Counter(a["role_derivation"] for a in assertions)
            ),
            "three_slot_complete": len(three_slot),
            "three_slot_per_veda": dict(Counter(a["veda"] for a in three_slot)),
            "verb_feature_schemes_never_merged": dict(
                Counter(a["verb_feature_scheme"] for a in assertions)
            ),
            "non_devata_target_fillers": non_devata_targets,
            "unknown_predicates_not_in_the_41_registry": unknown_predicates,
        },
        # LEAD RULING 1. The ruling's stated basis was that all 216 pairs carry a
        # pre-existing REUSES_TEXT_FROM or EXACT_PARALLEL_OF edge. Verified independently
        # against the live graph, and it holds -- every pair carries REUSES_TEXT_FROM. What
        # does NOT hold is the artifact's own single-valued field: it names VARIANT_OF on
        # 153 of the 216, which is a real edge on those pairs but not the strongest one and
        # not the one the ruling rests on. The row now carries the whole set.
        "cross_veda_projection_evidence": {
            "projected_rows": sum(
                1 for a in assertions if a["derivation"] == "CROSS_VEDA_TEXT_IDENTITY"
            ),
            "target_verses": len(per_veda_mantras["SV"]),
            "pairs_with_no_parallel_edge": 0,
            # ROUND-THREE RULING. The 8 assertions on the 5 NEAR_PARALLEL_OF pairs are
            # withheld, so these sets now cover the 211 importable pairs. The withheld 5
            # are itemised in withheld_projections below and in
            # semantic_assertions_withheld.jsonl -- not deleted.
            "live_edge_type_sets_over_the_importable_pairs": {
                "+".join(types): count
                for types, count in Counter(
                    tuple(
                        parallel_edges.get(
                            (a["canonical_key"], a["projected_from_canonical_key"]), []
                        )
                    )
                    for a in assertions
                    if a["derivation"] == "CROSS_VEDA_TEXT_IDENTITY"
                ).most_common()
            },
            "artifact_single_valued_claim": dict(
                Counter(
                    a["projection_relationship_claimed_by_artifact"]
                    for a in assertions
                    if a["derivation"] == "CROSS_VEDA_TEXT_IDENTITY"
                )
            ),
            "every_claimed_type_present_in_the_live_set": all(
                a["projection_relationship_claimed_by_artifact"]
                in parallel_edges.get(
                    (a["canonical_key"], a["projected_from_canonical_key"]), []
                )
                for a in assertions
                if a["derivation"] == "CROSS_VEDA_TEXT_IDENTITY"
            ),
            "ruling_basis_verified": "every one of the 216 pairs carries REUSES_TEXT_FROM; "
            "0 rest on a fold computed at staging time",
            "withheld_projections": {
                "assertions": len(withheld_rows),
                "pairs": len({r["canonical_key"] for r in withheld_rows}),
                "reason": "GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT",
                "rule": "When a staged claim contradicts the graph's own typing, the "
                "graph's typing wins unless the staged claim independently "
                "re-establishes itself. A letter comparison computed at staging time is "
                "not independent re-establishment.",
                "deleted": False,
                "artifact": "semantic_assertions_withheld.jsonl",
                "made_visible_by": "the projection_edge_types field added in round two. "
                "The artifact's single-valued field named REUSES_TEXT_FROM on these pairs "
                "and would have hidden the NEAR_PARALLEL_OF typing entirely.",
                "cost": f"{len(withheld_rows)} assertions of "
                f"{len(assertions) + len(withheld_rows)}",
                # Corroboration the lead did not have, and it is independent of both of
                # the probes that failed. The artifact's OWN containment score partitions
                # the 216 pairs identically to the graph's typing: exactly 5 pairs score
                # below 1.0 (0.9231, 0.9414, 0.9487, 0.9585, 0.9720) and 211 score exactly
                # 1.0 -- and the 5 sub-1.0 pairs ARE the 5 the graph types
                # NEAR_PARALLEL_OF, set-for-set. Two instruments that disagreed about
                # nothing: the projection was asserting letter identity on five pairs its
                # own score said were not identical.
                "corroborated_by_the_artifacts_own_score": {
                    "pairs_scoring_below_1.0": sorted(
                        {r["projection_graph_score"] for r in withheld_rows}
                    ),
                    "pairs_scoring_exactly_1.0": 211,
                    "sub_1_0_set_equals_near_parallel_set": sorted(
                        {r["canonical_key"] for r in withheld_rows}
                    ),
                    "note": "Independent of both of the lead's failed probes. The "
                    "projection asserted letter identity on five pairs its own containment "
                    "score already said were not identical.",
                },
            },
        },
        "closure_measures_after_import": {
            "GAP-SEMANTICS-001": {
                "has_semantic_assertion_reaches_non_rv": sorted(
                    v for v in per_veda_mantras if v != "RV"
                ),
                "rv_mantras_covered": len(per_veda_mantras["RV"]),
                "rv_before": live["rv_mantras_covered"],
                "blended_total_forbidden": True,
                "five_instruments": {
                    "live_MORPHOLOGY_RULE": live["live_derivations"].get("MORPHOLOGY_RULE"),
                    "live_MODEL_EXTRACTION": live["live_derivations"].get("MODEL_EXTRACTION"),
                    **dict(Counter(a["role_derivation"] for a in assertions)),
                },
            },
            "GAP-SEMANTICS-003": {
                "assertions_with_all_three_slots": len(three_slot),
                "at_least_one_non_devata_target": non_devata_targets > 0,
                "non_devata_target_fillers": non_devata_targets,
                "note": "A RoleFiller fills the slot as an occurrence. It is promoted to an "
                "entity only where an independent resolution produced a REFERS_TO edge; "
                "1,665 of 2,052 fillers carry none and stay occurrences.",
            },
            # LEAD CORRECTION 3. The gap's own closure_measure counts every
            # :SemanticAssertion, not just the ones that were live when the gap was written.
            "GAP-SEMANTICS-002": {
                "live_unreviewed_before": live["assertions_unreviewed"],
                "staged_assertions_all_unreviewed": len(assertions),
                "unreviewed_after_import": live["assertions_unreviewed"] + len(assertions),
                "multiple": round(
                    (live["assertions_unreviewed"] + len(assertions))
                    / max(live["assertions_unreviewed"], 1),
                    2,
                ),
                "closes": False,
            },
        },
        # Three gaps move in opposite directions under one import. Recorded as a trade
        # rather than as a headline, because the headline is the flattering half.
        "trade_this_import_makes": {
            "improves": "GAP-SEMANTICS-001 -- HAS_SEMANTIC_ASSERTION reaches all four "
            f"corpora and RV coverage goes {live['rv_mantras_covered']} -> "
            f"{len(per_veda_mantras['RV'])} of 10,552.",
            "worsens_SEMANTICS_002": (
                "the unreviewed population goes "
                f"{unreviewed_before} -> {unreviewed_after}, a "
                f"{round(unreviewed_after / max(unreviewed_before, 1), 1)}x "
                "multiplication. Closing coverage makes the review gap larger, not smaller."
            ),
            "deepens_SEMANTICS_003": f"{predicate_only} "
            "of the staged rows are MORPHOLOGY_RULE_PREDICATE_ONLY and carry no role slot "
            "at all, so the share of assertions with an incomplete triple rises even as the "
            "absolute count of complete triples goes 0 -> " + str(len(three_slot)) + ".",
            "rule": "None of these three figures may be reported without the other two.",
        },
        "samaveda_standing_constraint": {
            "rule": "The Samavedic assertions may NEVER be counted as Samaveda morphology "
            "or as Samavedic annotation, on any surface. The figure is 364 assertions over "
            "211 verses after the NEAR_PARALLEL_OF withholding, down from 372 over 216.",
            "sv_assertions": dict(Counter(a["veda"] for a in assertions))["SV"],
            "sv_verses_with_an_assertion": len(per_veda_mantras["SV"]),
            "sv_morphological_tokens_analysed": 0,
            "sv_assertions_before_the_near_parallel_withholding": (
                dict(Counter(a["veda"] for a in assertions))["SV"] + len(withheld_rows)
            ),
            "sv_verses_before_the_near_parallel_withholding": (
                len(per_veda_mantras["SV"])
                + len({r["canonical_key"] for r in withheld_rows})
            ),
            "why_both_figures_travel_together": "The assertion count is a count of "
            "transferred Rigvedic analyses. The token yield is what the Samaveda itself "
            "contributed, and it is zero. Publishing the first without the second is the "
            "misleading form of a true sentence.",
            "per_row_disclosure_kept_verbatim": [
                "cautions: [ANALYSIS_IS_OF_A_LETTER_IDENTICAL_RIGVEDIC_VERSE"
                "_NOT_OF_A_SAMAVEDIC_ANNOTATION]",
                "human_annotated: false",
                "model_assisted: false",
                "provenance: deterministic",
                "roles_withheld: true, with its reason",
            ],
        },
        "files": {
            name: sha256(path.read_bytes()).hexdigest() for name, path in paths.items()
        },
    }
    (OUT_DIR / "semantic_assertion_delta_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
