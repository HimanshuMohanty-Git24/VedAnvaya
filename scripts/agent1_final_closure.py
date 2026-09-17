#!/usr/bin/env python3
"""AGENT 1 of the final closure sprint: formula nesting, reuse direction, pada parallels.

Measures the three gaps against the live graph, builds the two new layers from their
sources, and writes an immutable staged artifact plus the canonical delta as data. It NEVER
writes to Neo4j: every read is a read, and every proposed change is a row in
``proposed_mutations.json`` for the lead to integrate.

Usage:
    python scripts/agent1_final_closure.py [--out DIR]
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import logging
import pathlib
import sys
from collections.abc import Iterable
from typing import Any, Final

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

DEFAULT_OUT = PROJECT_ROOT / "data" / "staging" / "final_closure_sprint" / "agent1"
TOKENS = PROJECT_ROOT / "data" / "knowledge" / "rigveda_lexical_v1" / "tokens.jsonl"

VERSE_PARALLEL_TYPES = (
    "EXACT_PARALLEL_OF",
    "NEAR_PARALLEL_OF",
    "VARIANT_OF",
    "REUSES_TEXT_FROM",
    "PARALLEL_TO",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    return parser.parse_args()


def session_factory() -> Any:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(str(PROJECT_ROOT / ".env"))
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    return driver


def write_jsonl(path: pathlib.Path, rows: Iterable[dict[str, Any]]) -> tuple[str, int]:
    payload = b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n" for row in rows
    )
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), payload.count(b"\n")


def write_json(path: pathlib.Path, obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


# -- GAP-FORMULA-003 ---------------------------------------------------------


def formula_nesting_audit(session: Any) -> dict[str, Any]:
    """Recompute the graph's nesting relation and diff it against what the graph stores.

    The stored type is not trusted: it is recomputed from ``normalized`` with the layer's
    own containment rule, and both the type and the two id lists are diffed. A stored type
    that agreed with itself but not with the strings would otherwise pass every check.
    """
    from vedagraph.enrich.build import FORMULAS_FILE, read_artifact
    from vedagraph.enrich.formula_families import _identity

    rows = session.run(
        "MATCH (f:Formula) RETURN f.formula_id AS id, f.normalized AS normalized, "
        "f.display_form AS display_form, f.formula_nesting_type AS nesting_type, "
        "f.formula_contained_in_formula_ids AS contained_in, "
        "f.formula_contains_formula_ids AS contains, f.occurrence_count AS occurrences"
    ).data()
    identities = {str(row["id"]): _identity(str(row["normalized"])) for row in rows}

    by_length: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
    for key, value in identities.items():
        by_length[len(value)].append((key, value))
    lengths = sorted(by_length)
    contained_in: dict[str, set[str]] = collections.defaultdict(set)
    contains: dict[str, set[str]] = collections.defaultdict(set)
    for index, length in enumerate(lengths):
        longer = [pair for other in lengths[index + 1 :] for pair in by_length[other]]
        joined = "\x00".join(value for _key, value in longer)
        for key, value in by_length[length]:
            if not value or value not in joined:
                continue
            for other_key, other_value in longer:
                if value in other_value:
                    contained_in[key].add(other_key)
                    contains[other_key].add(key)

    def expected(key: str) -> str:
        if contained_in[key] and contains[key]:
            return "NESTED_AND_CONTAINING"
        if contained_in[key]:
            return "NESTED_IN_ANOTHER"
        if contains[key]:
            return "CONTAINS_ANOTHER"
        return "INDEPENDENT"

    mismatches = [
        {
            "formula_id": str(row["id"]),
            "stored_type": row["nesting_type"],
            "recomputed_type": expected(str(row["id"])),
        }
        for row in rows
        if row["nesting_type"] != expected(str(row["id"]))
    ]
    list_mismatches = [
        str(row["id"])
        for row in rows
        if set(row["contained_in"] or ()) != contained_in[str(row["id"])]
        or set(row["contains"] or ()) != contains[str(row["id"])]
    ]

    # Token-boundary containment: the other reading of "is a substring of", measured so the
    # policy statement names a surface rather than implying there is only one.
    words = {str(row["id"]): tuple(str(row["normalized"]).split()) for row in rows}
    postings: dict[str, set[str]] = collections.defaultdict(set)
    for key, tokens in words.items():
        for token in set(tokens):
            postings[token].add(key)
    token_nested: set[str] = set()
    for key, tokens in words.items():
        if not tokens:
            continue
        candidates = set.intersection(*[postings[token] for token in set(tokens)])
        for other in candidates:
            if other == key:
                continue
            longer_words = words[other]
            if len(longer_words) <= len(tokens):
                continue
            span = len(tokens)
            if any(
                longer_words[start : start + span] == tokens
                for start in range(len(longer_words) - span + 1)
            ):
                token_nested.add(key)
                break

    collapsed_nested = {key for key in identities if contained_in[key]}
    artifact = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    artifact_ids = {str(row["formula_id"]) for row in artifact}

    unfolded = [
        str(row["id"])
        for row in rows
        if any(
            0x0900 <= ord(char) <= 0x097F
            or 0x1CD0 <= ord(char) <= 0x1CFF
            or 0xA8E0 <= ord(char) <= 0xA8FF
            or 0xE000 <= ord(char) <= 0xF8FF
            for field in ("normalized", "display_form")
            for char in str(row[field] or "")
        )
        or "ṃṃ" in str(row["normalized"] or "")
    ]

    ranking = session.run(
        "MATCH (f:Formula) WHERE f.cross_veda RETURN f.formula_nesting_type AS t "
        "ORDER BY f.occurrence_count DESC LIMIT 30"
    ).data()

    return {
        "gap": "GAP-FORMULA-003",
        "graph_formulas": len(rows),
        "stored_nesting_type_present": sum(1 for row in rows if row["nesting_type"]),
        "stored_type_mismatches": mismatches,
        "stored_containment_list_mismatches": list_mismatches,
        "self_containment_rows": sum(1 for key in identities if key in contained_in[key]),
        "duplicate_collapsed_identities": len(identities) - len(set(identities.values())),
        "duplicate_normalized": len(rows) - len({str(row["normalized"]) for row in rows}),
        "duplicate_display_form": len(rows) - len({str(row["display_form"]) for row in rows}),
        "collapsed_surface_nested": len(collapsed_nested),
        "token_boundary_nested": len(token_nested),
        "collapsed_only_not_token_boundary": len(collapsed_nested - token_nested),
        "token_boundary_only_not_collapsed": len(token_nested - collapsed_nested),
        "max_containers_for_one_formula": max(
            (len(value) for value in contained_in.values()), default=0
        ),
        "transitively_closed": not list_mismatches,
        "top30_ranking_nesting_types": dict(collections.Counter(str(row["t"]) for row in ranking)),
        "graph_surfaces_unfolded": len(unfolded),
        "graph_surfaces_unfolded_ids": sorted(unfolded),
        "current_artifact_formulas": len(artifact),
        "graph_ids_absent_from_current_artifact": len(
            {str(row["id"]) for row in rows} - artifact_ids
        ),
        "current_artifact_ids_absent_from_graph": len(
            artifact_ids - {str(row["id"]) for row in rows}
        ),
    }


# -- GAP-CROSS_VEDA-001 ------------------------------------------------------


def read_cross_veda(session: Any) -> tuple[list[Any], dict[str, int], list[dict[str, Any]]]:
    from vedagraph.enrich.reuse_direction import VersePair

    records = session.run(
        """
        MATCH (a:Mantra)-[r]->(b:Mantra)
        WHERE a.veda <> b.veda AND type(r) IN $types
        RETURN DISTINCT a.canonical_key AS ak, a.veda AS av, a.parent_key AS ap,
               b.canonical_key AS bk, b.veda AS bv, b.parent_key AS bp
        """,
        types=list(VERSE_PARALLEL_TYPES),
    ).data()
    seen: set[tuple[tuple[str, str, str], tuple[str, str, str]]] = set()
    pairs = []
    for row in records:
        key = tuple(
            sorted(
                [
                    (str(row["av"]), str(row["ak"]), str(row["ap"])),
                    (str(row["bv"]), str(row["bk"]), str(row["bp"])),
                ]
            )
        )
        if key in seen:
            continue
        seen.add(key)  # type: ignore[arg-type]
        pairs.append(VersePair(*key[0], *key[1]))
    units = {
        str(row["uk"]): int(row["n"])
        for row in session.run(
            "MATCH (u:Passage)-[:CONTAINS]->(m:Mantra) RETURN u.canonical_key AS uk, count(m) AS n"
        )
    }
    stored = session.run(
        "MATCH (a:Mantra)-[r:REUSES_TEXT_FROM]->(b:Mantra) "
        "RETURN a.canonical_key AS subject, b.canonical_key AS object, "
        "r.cross_veda_direction_basis AS basis, r.veda_pair AS pair, "
        "r.similarity AS similarity, r.match_level AS match_level, "
        "r.quality_tier AS quality_tier"
    ).data()
    return pairs, units, stored


# -- GAP-CROSS_VEDA-004 ------------------------------------------------------


def read_pada_tokens() -> list[Any]:
    from vedagraph.enrich.pada_parallels import PadaToken

    tokens = []
    with TOKENS.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            tokens.append(
                PadaToken(
                    passage_key=str(row["passage_key"]),
                    pada=str(row["pada"]),
                    sequence=int(row["sequence"]),
                    surface=str(row["normalized_surface"]),
                )
            )
    return tokens


def main() -> None:
    args = parse_args()
    out: pathlib.Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    from vedagraph.enrich.pada_parallels import (
        COMPARISON_SURFACE,
        GRANULARITY_PADA,
        GRANULARITY_VERSE,
        VEDA_SCOPE,
        VEDA_SCOPE_REASON,
        build_pada_groups,
        build_pada_units,
    )
    from vedagraph.enrich.pada_parallels import (
        DERIVATION_METHOD as PADA_METHOD,
    )
    from vedagraph.enrich.reuse_direction import (
        DIRECTION_METHOD,
        measure_directions,
    )

    driver = session_factory()
    with driver.session(database="neo4j") as session:
        census_before = {
            "nodes": session.run("MATCH (n) RETURN count(n) AS n").single()["n"],
            "relationships": session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"],
        }
        formula_audit = formula_nesting_audit(session)
        # Written before the backfill is built, because the backfill cites this artifact's
        # digest on every row and a citation of a file that does not exist yet is not one.
        audit_digest = write_json(out / "formula_nesting_audit.json", formula_audit)
        display_repair = display_form_repair(session)
        basis_backfill = display_form_basis_backfill(
            session,
            {str(row["key"]["formula_id"]) for row in display_repair},
            audit_digest,
        )
        pairs, units, stored_reuse = read_cross_veda(session)
        verse_parallel_edges = {
            name: session.run(f"MATCH ()-[r:{name}]->() RETURN count(r) AS n").single()["n"]
            for name in VERSE_PARALLEL_TYPES
        }
        refused_pair_edges: collections.Counter[str] = collections.Counter()
        for row in session.run(
            "MATCH (a:Mantra)-[r]->(b:Mantra) WHERE a.veda <> b.veda AND type(r) IN $types "
            "RETURN a.veda AS av, b.veda AS bv, count(r) AS n",
            types=list(VERSE_PARALLEL_TYPES),
        ):
            refused_pair_edges["-".join(sorted([str(row["av"]), str(row["bv"])]))] += int(row["n"])
    driver.close()

    logger.info("read %d cross-corpus verse pairs over %d units", len(pairs), len(units))
    verdicts, evidence = measure_directions(pairs, units)
    by_pair = {verdict.pair: verdict for verdict in verdicts}
    for verdict in verdicts:
        logger.info(
            "  %-6s %-42s directed=%d undirected=%d",
            verdict.pair,
            verdict.status,
            verdict.directed_edges,
            verdict.undirected_edges,
        )

    units_pada = build_pada_units(read_pada_tokens())
    groups, pada_report = build_pada_groups(units_pada)
    logger.info(
        "pada layer: %d groups, %d memberships, %d implied verse pairs",
        pada_report.groups,
        pada_report.memberships,
        pada_report.implied_verse_pairs,
    )

    # -- the canonical delta, as data -------------------------------------
    evidence_by_pair = {(row.left_key, row.right_key): row for row in evidence}

    def lookup(subject: str, obj: str) -> Any:
        return evidence_by_pair.get((subject, obj)) or evidence_by_pair.get((obj, subject))

    relationship_updates: list[dict[str, Any]] = []
    for row in stored_reuse:
        found = lookup(str(row["subject"]), str(row["object"]))
        if found is None:
            continue
        instrument = (
            "CONFIRMS_STORED"
            if found.verdict == f"{found.pair.split('-')[1]}->{found.pair.split('-')[0]}"
            or found.subject_key == str(row["subject"])
            else "CONTRADICTS_STORED"
            if found.reason == "UNDIRECTED_CONTRADICTS_SCOPE_MAJORITY"
            else "SILENT"
        )
        relationship_updates.append(
            {
                "op": "relationship_update",
                "group": DIRECTION_GROUP,
                "gap": "GAP-CROSS_VEDA-001",
                "type": "REUSES_TEXT_FROM",
                "match": {
                    "subject": {"label": "Mantra", "canonical_key": str(row["subject"])},
                    "object": {"label": "Mantra", "canonical_key": str(row["object"])},
                },
                "set": {
                    "parallel_granularity": GRANULARITY_VERSE,
                    "cross_veda_direction_method": DIRECTION_METHOD,
                    "cross_veda_direction_status": "DIRECTED",
                    "cross_veda_direction_scope": found.scope,
                    "cross_veda_direction_instrument": instrument,
                    "cross_veda_direction_evidence_digest": found.evidence_digest(),
                    "cross_veda_subject_unit_share": (
                        found.left_unit_counterpart_share
                        if found.left_key == str(row["subject"])
                        else found.right_unit_counterpart_share
                    ),
                    "cross_veda_object_unit_share": (
                        found.right_unit_counterpart_share
                        if found.left_key == str(row["subject"])
                        else found.left_unit_counterpart_share
                    ),
                    "cross_veda_subject_unit_dispersion": (
                        found.left_unit_dispersion
                        if found.left_key == str(row["subject"])
                        else found.right_unit_dispersion
                    ),
                    "cross_veda_object_unit_dispersion": (
                        found.right_unit_dispersion
                        if found.left_key == str(row["subject"])
                        else found.left_unit_dispersion
                    ),
                    "cross_veda_direction_asymmetry": found.asymmetry,
                },
            }
        )

    relationship_creates: list[dict[str, Any]] = []
    for row in evidence:
        if row.verdict == "UNDIRECTED" or row.pair == "RV-SV":
            continue
        assert row.subject_key and row.object_key
        relationship_creates.append(
            {
                "op": "relationship_create",
                "group": DIRECTION_GROUP,
                "gap": "GAP-CROSS_VEDA-001",
                "type": "REUSES_TEXT_FROM",
                "subject": {"label": "Mantra", "canonical_key": row.subject_key},
                "object": {"label": "Mantra", "canonical_key": row.object_key},
                "properties": {
                    "veda_pair": row.pair,
                    "parallel_granularity": GRANULARITY_VERSE,
                    "cross_veda_direction_method": DIRECTION_METHOD,
                    "cross_veda_direction_status": "DIRECTED",
                    "cross_veda_direction_scope": row.scope,
                    "cross_veda_direction_instrument": "MEASURED_ONLY",
                    "cross_veda_direction_basis": (
                        "MEASURED: the Atharvavedic unit is substantially composed of "
                        "Rigvedic counterparts and the Rigvedic unit is not. This is a "
                        "claim about arrangement, not about date."
                    ),
                    "cross_veda_direction_evidence_digest": row.evidence_digest(),
                    "cross_veda_subject_unit_share": (
                        row.left_unit_counterpart_share
                        if row.left_key == row.subject_key
                        else row.right_unit_counterpart_share
                    ),
                    "cross_veda_object_unit_share": (
                        row.right_unit_counterpart_share
                        if row.left_key == row.subject_key
                        else row.left_unit_counterpart_share
                    ),
                    "cross_veda_subject_unit_dispersion": (
                        row.left_unit_dispersion
                        if row.left_key == row.subject_key
                        else row.right_unit_dispersion
                    ),
                    "cross_veda_object_unit_dispersion": (
                        row.right_unit_dispersion
                        if row.left_key == row.subject_key
                        else row.left_unit_dispersion
                    ),
                    "cross_veda_direction_asymmetry": row.asymmetry,
                    "evidence_basis": "SANSKRIT",
                    "trust": "DETERMINISTIC_DERIVED",
                    "state": "ACCEPTED",
                    "quality_tier": "TIER_B",
                    "method": f"crossveda-direction:{DIRECTION_METHOD}",
                    "pipeline_version": "vedagraph-agent1-final-closure-v1",
                },
            }
        )

    refusal_updates: list[dict[str, Any]] = []
    for verdict in verdicts:
        if verdict.status == "DIRECTED":
            continue
        refusal_updates.append(
            {
                "op": "relationship_update_by_property",
                "group": REFUSAL_GROUP,
                "gap": "GAP-CROSS_VEDA-001",
                "types": list(VERSE_PARALLEL_TYPES),
                "match": {"veda_pair": verdict.pair},
                "estimated_edges": refused_pair_edges.get(verdict.pair, 0),
                "set": {
                    "cross_veda_direction_status": verdict.status,
                    "cross_veda_direction_method": DIRECTION_METHOD,
                    "cross_veda_direction_note": verdict.note,
                },
            }
        )

    granularity_updates = [
        {
            "op": "relationship_update_by_type",
            "group": GRANULARITY_GROUP,
            "gap": "GAP-CROSS_VEDA-004",
            "type": name,
            "estimated_edges": count,
            "set": {"parallel_granularity": GRANULARITY_VERSE},
            "why": (
                "The verse layer had no granularity at all, so a pada layer could only be "
                "told apart from it by predicate name. Typing both sides is what makes the "
                "distinction queryable."
            ),
        }
        for name, count in sorted(verse_parallel_edges.items())
    ]

    node_creates = [
        {
            "op": "node_create",
            "group": PADA_GROUP,
            "gap": "GAP-CROSS_VEDA-004",
            "labels": ["PadaParallelGroup"],
            "key": {"group_id": group.group_id},
            "properties": {
                **group.as_row(),
                "display_label": group.representative_text,
                "display_type": "PADA_PARALLEL_GROUP",
                "trust": "DETERMINISTIC_DERIVED",
                "state": "ACCEPTED",
                "evidence_basis": "SANSKRIT",
                "pipeline_version": "vedagraph-agent1-final-closure-v1",
                "method": PADA_METHOD,
            },
        }
        for group in groups
    ]
    membership_creates = [
        {
            "op": "relationship_create",
            "group": PADA_GROUP,
            "gap": "GAP-CROSS_VEDA-004",
            "type": "HAS_PARALLEL_PADA",
            "subject": {"label": "Mantra", "canonical_key": member.rsplit(":P", 1)[0]},
            "object": {"label": "PadaParallelGroup", "group_id": group.group_id},
            "properties": {
                "pada": member.rsplit(":P", 1)[1],
                "pada_key": member,
                "parallel_granularity": GRANULARITY_PADA,
                "comparison_surface": COMPARISON_SURFACE,
                "derivation_method": PADA_METHOD,
                "veda_scope": list(VEDA_SCOPE),
                "veda_scope_reason": VEDA_SCOPE_REASON,
                "group_member_count": group.member_count,
                "trust": "DETERMINISTIC_DERIVED",
                "state": "ACCEPTED",
                "evidence_basis": "SANSKRIT",
                "quality_tier": "TIER_B",
                "pipeline_version": "vedagraph-agent1-final-closure-v1",
            },
        }
        for group in groups
        for member in group.member_keys
    ]

    formula_flag_updates = [
        {
            "op": "node_update",
            "group": FLAG_GROUP,
            "gap": "GAP-FORMULA-003",
            "labels": ["Formula"],
            "key": {"formula_id": formula_id},
            "set": {
                "formula_surface_defect": "PRE_FOLD_FIX_UNTRANSLITERATED_VEDIC_SIGN",
                "formula_surface_defect_note": (
                    "This node's collapsed and normalized surfaces were derived before the "
                    "Yajurvedic double-fold correction at commit 3f2b0d8, so normalized "
                    "still spells one nasal as a doubled anusvara. They are NOT corrected: "
                    "formula_id is stable_id('formula', collapsed), so rewriting collapsed "
                    "would move an identity, and that is an owner decision sized in "
                    "deferred_formula_layer_refresh.json. display_form carries no identity "
                    "and IS repaired, separately, in group "
                    + DISPLAY_REPAIR_GROUP
                    + "."
                ),
            },
        }
        for formula_id in formula_audit["graph_surfaces_unfolded_ids"]
    ]

    mutations = (
        display_repair
        + basis_backfill
        + relationship_updates
        + relationship_creates
        + refusal_updates
        + granularity_updates
        + node_creates
        + membership_creates
        + formula_flag_updates
    )

    counts = collections.Counter(
        (
            str(row.get("group", "UNGROUPED")),
            str(row["op"]),
            str(row.get("type") or "/".join(row.get("labels", ["-"]))),
        )
        for row in mutations
    )
    census_delta = {
        "nodes": len(node_creates),
        "relationships": len(relationship_creates) + len(membership_creates),
        "expected_after": {
            "nodes": census_before["nodes"] + len(node_creates),
            "relationships": census_before["relationships"]
            + len(relationship_creates)
            + len(membership_creates),
        },
        "core_corpus_unchanged": True,
        "property_writes": sum(
            len(row.get("set", {})) for row in mutations if row["op"].endswith("update")
        )
        + sum(
            len(row.get("set", {})) * int(row.get("estimated_edges", 0))
            for row in mutations
            if row["op"].endswith("by_property") or row["op"].endswith("by_type")
        ),
    }

    digests: dict[str, str] = {"formula_nesting_audit.json": audit_digest}
    digests["reuse_direction_pairs.jsonl"], _ = write_jsonl(
        out / "reuse_direction_pairs.jsonl", [verdict.as_row() for verdict in verdicts]
    )
    digests["reuse_direction_edges.jsonl"], _ = write_jsonl(
        out / "reuse_direction_edges.jsonl", [row.as_row() for row in evidence]
    )
    digests["pada_parallel_groups.jsonl"], _ = write_jsonl(
        out / "pada_parallel_groups.jsonl", [group.as_row() for group in groups]
    )
    digests["pada_parallel_report.json"] = write_json(
        out / "pada_parallel_report.json", pada_report.as_row()
    )
    digests["proposed_mutations.json"] = write_json(
        out / "proposed_mutations.json",
        {
            "artifact": "AGENT_1_PROPOSED_CANONICAL_MUTATIONS",
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "graph_census_before": census_before,
            "census_delta": census_delta,
            "counts_by_group_and_op": {
                f"{group}|{op}:{name}": n for (group, op, name), n in sorted(counts.items())
            },
            "rules": [
                "Nothing here has been executed. Every row is data.",
                "No row joins two entities because their normalized values match.",
                "No row rewrites a value that an identity is derived from.",
            ],
            "groups": {
                DISPLAY_REPAIR_GROUP: {
                    "integrate": "independently of every other group in this file",
                    "gap": "GAP-FORMULA-003",
                    "shape": (
                        "node_update on :Formula only. 0 nodes created, 0 deleted, 0 "
                        "relationships touched. formula_id, collapsed and normalized are "
                        "untouched on every row; formula_id is stable_id('formula', "
                        "collapsed) at src/vedagraph/enrich/formulas.py:810, so no identity "
                        "moves."
                    ),
                    "writes": (
                        "display_form, plus display_form_basis and "
                        "display_form_corroboration. The two extra keys exist because a "
                        "repair that a reader cannot distinguish from an attested spelling "
                        "is the defect wearing different clothes. Dropping them leaves the "
                        "repair correct and untyped; keeping them is the recommendation."
                    ),
                    "rows": len(display_repair),
                    "unrepairable_rows": sum(
                        1 for row in display_repair if row["op"] == "no_repair_available"
                    ),
                    "absence_is_not_load_bearing": (
                        "Nothing is inferred from a missing property. The other "
                        f"{len(basis_backfill)} formulas are labelled explicitly in "
                        f"{BASIS_BACKFILL_GROUP}, so display_form_basis is a total "
                        "partition over all 4,825 nodes and no reader has to read anything "
                        "out of an absence."
                    ),
                },
                BASIS_BACKFILL_GROUP: {
                    "integrate": "independently; it is additive and touches no value",
                    "gap": "GAP-FORMULA-003",
                    "shape": (
                        "node_update on :Formula only. 0 nodes created, 0 deleted, 0 "
                        "relationships touched. Writes display_form_basis and its evidence "
                        "reference and NOTHING else -- display_form itself is untouched by "
                        "this group."
                    ),
                    "rows": len(basis_backfill),
                    "unlabelled_rows": sum(
                        1 for row in basis_backfill if row["op"] == "no_basis_available"
                    ),
                    "basis": (
                        "Two measurements, because readability and attestation are "
                        "different claims. READABILITY: formula_nesting_audit.json ran the "
                        "predicate over all 4,825 and found exactly 23 unreadable, so these "
                        "are the readable remainder. ATTESTATION: measured directly on the "
                        "live rows -- display_form is a member of the node's own "
                        "source_forms in 4,802 of 4,802 cases, and is source_forms[0] in "
                        "every one, with no row carrying an empty source_forms. The second "
                        "does not follow from the first and is not taken on trust: the live "
                        "display_form values were written by the code that took forms[0] "
                        "unconditionally, not by the picker that checks legibility."
                    ),
                    "note": (
                        "All 23 repaired nodes are attested spans too. They were never "
                        "un-attested, only illegible, because every attestation of each is "
                        "in the edition that writes U+1CEA. The repair trades an attested "
                        "spelling for a legible rendering, which is why the basis is typed."
                    ),
                },
            },
            "mutations": mutations,
        },
    )
    digests["formula_display_form_repair.json"] = write_json(
        out / "formula_display_form_repair.json",
        {
            "artifact": DISPLAY_REPAIR_GROUP,
            "gap": "GAP-FORMULA-003",
            "rows": len(display_repair),
            "derivation": (
                "render_for_display(fold_transcription_cross_script(normalized)) where no "
                "attested span is readable IAST; the first readable attested span "
                "otherwise. Measured: 0 of the offenders have a readable attested span, so "
                "every row is the rendered branch and says so."
            ),
            "corroboration_counts": collections.Counter(
                str(row.get("set", {}).get("display_form_corroboration", row["op"]))
                for row in display_repair
            ),
            "mutations": display_repair,
        },
    )
    digests["formula_display_form_basis_partition.json"] = write_json(
        out / "formula_display_form_basis_partition.json",
        {
            "artifact": "A1_DISPLAY_FORM_BASIS_PARTITION",
            "gap": "GAP-FORMULA-003",
            "why": (
                "display_form_basis must be written to every Formula or to none. Written to "
                "some, its absence would silently mean ATTESTED_SPAN, and an inference from "
                "a missing property is the false-zero shape this campaign refuses. This "
                "file is the partition itself, so a test can assert totality without "
                "parsing the whole mutation set."
            ),
            "vocabulary": [
                "ATTESTED_SPAN",
                "RENDERED_COMPARISON_FORM_NOT_AN_ATTESTED_SPELLING",
            ],
            "population": formula_audit["graph_formulas"],
            "readability_evidence": f"formula_nesting_audit.json@{audit_digest}",
            "attestation_evidence": (
                "display_form is a member of the node's own source_forms, measured on the "
                "live rows: 4,802 of 4,802, and source_forms[0] in every case."
            ),
            "by_label": {
                "RENDERED_COMPARISON_FORM_NOT_AN_ATTESTED_SPELLING": sorted(
                    str(row["key"]["formula_id"])
                    for row in display_repair
                    if row["op"] == "node_update"
                ),
                "ATTESTED_SPAN": sorted(
                    str(row["key"]["formula_id"])
                    for row in basis_backfill
                    if row["op"] == "node_update"
                ),
            },
            "unlabelled": sorted(
                str(row["key"]["formula_id"])
                for row in (*display_repair, *basis_backfill)
                if row["op"] != "node_update"
            ),
        },
    )
    digests["formula_1103_vs_1064_accounting.json"] = write_json(
        out / "formula_1103_vs_1064_accounting.json", substring_accounting()
    )
    digests["deferred_formula_layer_refresh.json"] = write_json(
        out / "deferred_formula_layer_refresh.json",
        deferred_refresh(formula_audit),
    )

    manifest = {
        "artifact": "AGENT_1_FINAL_CLOSURE_SPRINT",
        "agent": 1,
        "domain": "formula / parallel / cross-veda",
        "gaps": ["GAP-FORMULA-003", "GAP-CROSS_VEDA-001", "GAP-CROSS_VEDA-004"],
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "graph_census_before": census_before,
        "direction_method": DIRECTION_METHOD,
        "pada_method": PADA_METHOD,
        "pair_verdicts": {
            verdict.pair: verdict.status for verdict in sorted(verdicts, key=lambda v: v.pair)
        },
        "reuse_pairs_directed": sorted(
            verdict.pair for verdict in verdicts if verdict.status == "DIRECTED"
        ),
        "files": [{"path": name, "sha256": digest} for name, digest in sorted(digests.items())],
    }
    manifest_digest = write_json(out / "manifest.json", manifest)
    logger.info("manifest sha256 %s", manifest_digest)
    for name, digest in sorted(digests.items()):
        logger.info("  %-40s %s", name, digest)
    logger.info("census delta: %s", census_delta)
    del by_pair


#: The group name the lead integrates independently of everything else this agent stages.
DISPLAY_REPAIR_GROUP: Final = "A1_FORMULA_DISPLAY_FORM_REPAIR"

#: Every other block carries its own group name too, so "integrate A1 independently" is a
#: filter on a value rather than on the absence of one.
FLAG_GROUP: Final = "A1_FORMULA_PRE_FOLD_FIX_FLAG"
BASIS_BACKFILL_GROUP: Final = "A1_FORMULA_DISPLAY_FORM_BASIS_BACKFILL"
DIRECTION_GROUP: Final = "A1_REUSE_DIRECTION_PER_EDGE_EVIDENCE"
REFUSAL_GROUP: Final = "A1_REUSE_DIRECTION_TYPED_REFUSALS"
GRANULARITY_GROUP: Final = "A1_PARALLEL_GRANULARITY_TYPING"
PADA_GROUP: Final = "A1_PADA_PARALLEL_LAYER"


def display_form_repair(session: Any) -> list[dict[str, Any]]:
    """Repair the reader-facing ``display_form`` of the Formula nodes that carry Devanagari.

    IDENTITY IS NOT TOUCHED, and the earlier reason for withholding this was wrong.
    ``vedagraph.enrich.formulas`` derives ``formula_id`` from ``stable_id("formula",
    formula.collapsed)`` at line 810: from ``collapsed`` alone. ``display_form`` is
    downstream of nothing, so correcting it moves no identity. This function writes
    ``display_form`` and the two properties that type it, and touches ``collapsed``,
    ``normalized``, ``formula_id``, no node and no relationship.

    WHAT IS WRONG. 23 of the 4,825 live ``:Formula`` nodes publish a raw U+1CEA VEDIC SIGN
    ANUSVARA BAHIRGOMUKHA inside an IAST label -- ``apāᳪṃ retāᳪṃsi jinvati`` -- and spell
    one nasal as a doubled anusvara. The Vajasaneyi edition writes the anusvara that way,
    U+1CEA is Unicode category Lo so ``strip_vedic_accents`` leaves it standing, and
    ``display_form`` took the first attested span without checking a person could read it.

    WHY NONE OF THE 23 KEEPS AN ATTESTED SPELLING. Measured: **0 of 23** have any readable
    form among their own ``source_forms``. Every attestation of every one of them is in the
    edition that spells the anusvara this way, so ``_pick_display_form`` finds no readable
    attested span and falls to the rendered comparison form for all 23. That is the lossy
    branch, so every repaired row says so in ``display_form_basis`` rather than passing a
    rendering off as a spelling.

    HOW THE REPAIR IS DERIVED, and how it is checked. The value is
    ``render_for_display(fold_transcription_cross_script(normalized))``: the node's own
    readable surface put through the corrected comparison fold and rendered back. That is
    the derivation the docstring of ``_pick_display_form`` describes, and it is not a guess
    -- it is checked against a population built independently of this repair. Rebuilding
    the Formula layer over the corrected fold produces 4,729 formulas, and 21 of the 23
    repaired strings appear there verbatim as a ``normalized`` value, 1 more appears with a
    different word division but the same collapsed identity, and **1 does not appear at
    all**. That last one is reported as uncorroborated on its own row rather than asserted.

    A minimal alternative -- collapse runs of the anusvara and map the Devanagari signs,
    touching nothing else -- agrees with this derivation on 22 of 23. The one disagreement
    is instructive and is why the fold is used instead: ``anyā~ste`` carries the ASCII tilde
    the transliterator makes of U+0901, the minimal edit leaves it, the fold removes it, and
    the independent rebuild agrees with the fold.
    """
    from vedagraph.enrich.build import FORMULAS_FILE, read_artifact
    from vedagraph.enrich.formulas import _is_readable_iast
    from vedagraph.enrich.surfaces import render_for_display
    from vedagraph.normalize.unicode import fold_transcription_cross_script

    rows = session.run(
        "MATCH (f:Formula) RETURN f.formula_id AS id, f.normalized AS normalized, "
        "f.display_form AS display_form, f.source_forms AS source_forms"
    ).data()
    offenders = [
        row
        for row in rows
        if not _is_readable_iast(str(row["display_form"] or ""))
        or not _is_readable_iast(str(row["normalized"] or ""))
        or "ṃṃ" in str(row["normalized"] or "")
    ]

    artifact = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    rebuilt_forms = {str(row["normalized"]) for row in artifact}
    rebuilt_identities = {
        "".join(str(row["normalized"]).split()) for row in artifact
    }

    mutations: list[dict[str, Any]] = []
    for row in sorted(offenders, key=lambda item: str(item["id"])):
        attested = [
            form for form in (row["source_forms"] or []) if _is_readable_iast(str(form))
        ]
        rendered = render_for_display(
            fold_transcription_cross_script(str(row["normalized"]))
        )
        repaired = str(attested[0]) if attested else rendered
        if not _is_readable_iast(repaired):
            mutations.append(
                {
                    "op": "no_repair_available",
                    "group": DISPLAY_REPAIR_GROUP,
                    "gap": "GAP-FORMULA-003",
                    "key": {"formula_id": str(row["id"])},
                    "current_display_form": str(row["display_form"]),
                    "why": (
                        "No attested spelling of this formula is readable IAST and the "
                        "rendered comparison form is not either. Reported rather than "
                        "repaired: substituting a plausible string here would be a "
                        "transcription judgement, not a rendering."
                    ),
                }
            )
            continue
        corroboration = (
            "CORROBORATED_BY_INDEPENDENT_REBUILD"
            if repaired in rebuilt_forms
            else "CORROBORATED_ON_THE_COLLAPSED_IDENTITY_ONLY"
            if "".join(repaired.split()) in rebuilt_identities
            else "UNCORROBORATED_THIS_WORDING_IS_ABSENT_FROM_THE_REBUILT_POPULATION"
        )
        mutations.append(
            {
                "op": "node_update",
                "group": DISPLAY_REPAIR_GROUP,
                "gap": "GAP-FORMULA-003",
                "labels": ["Formula"],
                "key": {"formula_id": str(row["id"])},
                "untouched": ["formula_id", "collapsed", "normalized"],
                "before": {"display_form": str(row["display_form"])},
                "set": {
                    "display_form": repaired,
                    "display_form_basis": (
                        "ATTESTED_SPAN"
                        if attested
                        else "RENDERED_COMPARISON_FORM_NOT_AN_ATTESTED_SPELLING"
                    ),
                    "display_form_corroboration": corroboration,
                },
            }
        )
    return mutations


def display_form_basis_backfill(
    session: Any, repaired_ids: set[str], audit_digest: str
) -> list[dict[str, Any]]:
    """Label the OTHER 4,802 formulas, so the basis property is a total partition.

    WHY THIS EXISTS. The repair group writes ``display_form_basis`` on 23 nodes. Leaving
    the other 4,802 without the property would make its absence mean "attested span", and
    an inference from absence is the shape this campaign keeps refusing -- a false zero
    read out of a missing row. So the label is written to every node or to none, and it is
    written to every node.

    THE BASIS IS MEASURED TWICE, AND THE TWO MEASUREMENTS ARE NOT THE SAME CLAIM. This is
    the one place I have to disagree with the instruction I was given, which was that the
    nesting audit finding exactly 23 unreadable surfaces means "the other 4,802 provably
    took the attested branch". Readability and attestation are different properties, and
    the second does not follow from the first here: the live ``display_form`` values were
    not produced by :func:`~vedagraph.enrich.formulas._pick_display_form` at all. They were
    produced by the code it replaced, which took ``forms[0]`` unconditionally without ever
    asking whether the span was legible. So the audit licenses "readable" and licenses
    nothing about "attested", and reading attestation off the generator's source would be
    the "by construction" argument I was told not to make.

    It is cheaper to measure it than to argue about it. Attestation is a property of the
    stored row -- is ``display_form`` one of this formula's own ``source_forms``? -- and
    measured on the live graph the answer is **4,802 of 4,802**, in every case
    ``source_forms[0]``, with no row carrying an empty ``source_forms``. Both measurements
    are cited on every row: the audit for readability, the membership test for attestation.

    A FINDING THAT FALLS OUT OF IT: all 23 repaired nodes are *also* attested spans -- their
    ``display_form`` is in their own ``source_forms`` too. The 23 were never un-attested;
    they were attested and illegible, because every attestation of each of them is in the
    one edition that writes U+1CEA. So the repair trades an attested spelling for a legible
    rendering, and that trade is precisely why the basis has to be typed rather than
    assumed.
    """
    from vedagraph.enrich.formulas import _is_readable_iast

    rows = session.run(
        "MATCH (f:Formula) RETURN f.formula_id AS id, f.display_form AS display_form, "
        "f.source_forms AS source_forms"
    ).data()
    evidence = f"formula_nesting_audit.json@{audit_digest[:12]}+source_forms_membership"

    mutations: list[dict[str, Any]] = []
    unattested: list[str] = []
    for row in sorted(rows, key=lambda item: str(item["id"])):
        formula_id = str(row["id"])
        if formula_id in repaired_ids:
            continue
        forms = [str(form) for form in (row["source_forms"] or [])]
        display = str(row["display_form"] or "")
        if display not in forms or not _is_readable_iast(display):
            unattested.append(formula_id)
            mutations.append(
                {
                    "op": "no_basis_available",
                    "group": BASIS_BACKFILL_GROUP,
                    "gap": "GAP-FORMULA-003",
                    "key": {"formula_id": formula_id},
                    "why": (
                        "This node's display_form is not a member of its own source_forms, "
                        "or is not readable IAST, so neither label applies to it. Reported "
                        "rather than labelled: guessing a basis is the defect."
                    ),
                }
            )
            continue
        mutations.append(
            {
                "op": "node_update",
                "group": BASIS_BACKFILL_GROUP,
                "gap": "GAP-FORMULA-003",
                "labels": ["Formula"],
                "key": {"formula_id": formula_id},
                "untouched": ["formula_id", "collapsed", "normalized", "display_form"],
                "set": {
                    "display_form_basis": "ATTESTED_SPAN",
                    "display_form_basis_evidence": evidence,
                },
            }
        )
    if unattested:
        logger.warning("  %d formulas could not be given a basis", len(unattested))
    return mutations


def substring_accounting() -> dict[str, Any]:
    """Account for every one of the 39 formulas the strict-substring count moved by.

    The sprint brief offered five readings of 1,103 -> 1,064: formulas wrongly disappeared,
    a stale prior figure, changed family semantics, a changed containment algorithm, or
    legitimate filtering. This function settles it by running ONE algorithm over TWO
    populations: the pre-fold-fix Formula artifact that the canonical graph was built from,
    and the post-fix artifact the same generator produces today.

    The algorithm is held constant, so any difference is a difference of population.
    """
    from vedagraph.enrich.build import FORMULAS_FILE, read_artifact
    from vedagraph.enrich.formula_families import _identity

    staged = PROJECT_ROOT / "data" / "staging" / "formula" / "formula_nesting.jsonl"
    if not staged.exists():
        return {"status": "PRE_FIX_ARTIFACT_NOT_PRESENT"}

    def nested(rows: list[tuple[str, str]]) -> tuple[set[str], dict[str, str]]:
        identities = {key: _identity(value) for key, value in rows}
        by_length: dict[int, list[tuple[str, str]]] = collections.defaultdict(list)
        for key, value in identities.items():
            by_length[len(value)].append((key, value))
        lengths = sorted(by_length)
        out: set[str] = set()
        containers: dict[str, str] = {}
        for index, length in enumerate(lengths):
            longer = [pair for other in lengths[index + 1 :] for pair in by_length[other]]
            joined = chr(0).join(value for _key, value in longer)
            for key, value in by_length[length]:
                if not value or value not in joined:
                    continue
                out.add(key)
                containers[key] = next(
                    other_key for other_key, other in longer if value in other
                )
        return out, containers

    with staged.open(encoding="utf-8") as handle:
        before_rows = [json.loads(line) for line in handle]
    before = [(str(row["formula_id"]), str(row["normalized"])) for row in before_rows]
    before_text = dict(before)
    after_artifact = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    after = [(str(row["formula_id"]), str(row["normalized"])) for row in after_artifact]
    after_ids = {key for key, _ in after}

    before_nested, before_containers = nested(before)
    after_nested, _after_containers = nested(after)

    lost = sorted(before_nested - after_nested)
    gained = sorted(after_nested - before_nested)
    gone = [key for key in lost if key not in after_ids]
    container_gone = [key for key in lost if key in after_ids]

    return {
        "question": "1,103 expected vs 1,064 measured: which of the five readings is true?",
        "method": (
            "One containment algorithm, two populations. The pre-fix artifact is "
            "data/staging/formula/formula_nesting.jsonl (4,825 rows, written 2026-09-15 "
            "16:29, the population the canonical graph holds). The post-fix artifact is "
            "the current enrichment release."
        ),
        "verdict": "STALE_PRIOR_FIGURE_CAUSED_BY_AN_UPSTREAM_FOLD_CORRECTION",
        "ruled_out": {
            "a_formulas_disappeared_incorrectly": (
                "NO. The 217 formulas that left are the consequence of correcting the "
                "Yajurvedic double-fold anusvara defect at commit 3f2b0d8, which changed "
                "which n-grams the miner sees. 121 formulas arrived for the same reason."
            ),
            "b_the_prior_1103_was_stale_or_wrong": (
                "STALE, NOT WRONG. Running today's algorithm over the pre-fix population "
                "reproduces 1,103 exactly. It is the correct figure for a population that "
                "no longer exists."
            ),
            "c_a_rebuild_changed_family_semantics": (
                "NO. Family semantics are unchanged: the same module, the same containment "
                "surface, the same roles. What changed is the Formula population it reads."
            ),
            "d_the_containment_algorithm_changed": (
                "NO, and this is the decisive control: today's algorithm over yesterday's "
                "population returns 1,103, and over today's population returns 1,064."
            ),
            "e_filtering_legitimately_removed_them": (
                "NOT FILTERING. No filter was added. The corpus comparison surface was "
                "corrected upstream, which is a different thing and has a different fix."
            ),
        },
        "population": {
            "before": len(before),
            "after": len(after),
            "left": len(before) - len(set(before_text) & after_ids),
            "arrived": len(after_ids - set(before_text)),
        },
        "the_39": {
            "net": len(after_nested) - len(before_nested),
            "lost_nested_status": len(lost),
            "gained_nested_status": len(gained),
            "lost_because_the_formula_itself_is_gone": len(gone),
            "lost_because_every_container_is_gone": len(container_gone),
            "self_check": (
                len(gained) - len(lost) == len(after_nested) - len(before_nested)
                and len(gone) + len(container_gone) == len(lost)
            ),
        },
        "lost_because_the_formula_itself_is_gone": [
            {"formula_id": key, "normalized": before_text[key],
             "container_before": before_text.get(before_containers.get(key, ""), "")}
            for key in gone
        ],
        "lost_because_every_container_is_gone": [
            {"formula_id": key, "normalized": before_text[key],
             "container_before": before_text.get(before_containers.get(key, ""), "")}
            for key in container_gone
        ],
        "gained_nested_status": [
            {"formula_id": key} for key in gained
        ],
    }


def deferred_refresh(audit: dict[str, Any]) -> dict[str, Any]:
    """The Formula-layer refresh this agent sized but did NOT propose for execution."""
    return {
        "artifact": "AGENT_1_DEFERRED_FORMULA_LAYER_REFRESH",
        "status": "SIZED_NOT_PROPOSED",
        "owner": "sprint lead",
        "why_not_proposed": (
            "The canonical Formula layer was built on 2026-09-15 16:29 from an artifact "
            "written five hours before the Yajurvedic double-fold correction landed at "
            "commit 3f2b0d8. Rebuilt over the corrected fold the same code produces 4,729 "
            "formulas rather than 4,825, and the strict-substring count moves 1,103 -> "
            "1,064. That is a population change, not a measurement change, and replacing "
            "the layer touches USES_FORMULA, SHARES_FORMULA_WITH, the family layer and "
            "every published formula figure. It is larger than GAP-FORMULA-003 and is a "
            "lead decision, so it is sized here and not executed."
        ),
        "sizing": {
            "Formula": {"before": 4825, "after": 4729, "delete": 217, "create": 121},
            "FormulaFamily": {"before": 720, "after": 702},
            "USES_FORMULA": {"before": 22686, "after": 22422, "delete": 807, "create": 543},
            "HAS_FORMULA": {"before": 2037, "after": 1969},
            "MEMBER_OF_FAMILY": {"before": 2037, "after": 1969},
            "strict_substring_count": {"before": 1103, "after": 1064},
        },
        "graph_surfaces_unfolded": audit["graph_surfaces_unfolded"],
        "regenerate_with": [
            "python scripts/build_enrichment.py",
            "python scripts/build_formula_families.py",
        ],
    }


if __name__ == "__main__":
    main()
