#!/usr/bin/env python3
"""Owner decision 3: SOMA-PRESSING stays, its weak aliases lose assertion authority.

The owner's ruling keeps ``VG:CONCEPT:SOMA-PRESSING`` as a canonical ritual object, bars
its weak lexical aliases from establishing identity on their own, names ``sute`` and
``sutasah`` as measured bad examples, and requires that every existing graph edge whose
sole evidence is a retired alias be re-evaluated and retired unless another independent
evidence basis supports it.

THE CRITERION IS MEASURED, NOT EDITORIAL
========================================

``h2_verdict = AMBIGUOUS_SURFACE`` in the quality artifact's per-alias soundness proof:
the alias's dominant human lemma holds under 80% of its occurrences in a published human
treebank. Three SOMA-PRESSING aliases meet it:

    sute      su 6 / suta 6   dominant share 0.500   named by the owner
    sutesu    su 2 / suta 2   dominant share 0.500   the same split, same formation
    sutasah   su 9 / suta 4   dominant share 0.692   named by the owner

``sutesu`` is not one of the owner's two examples and is retired anyway, because it is
selected by the same measurement at the same value as ``sute``: retiring one and keeping
the other would be arbitrary. Per-alias rather than per-layer, because a layer-level
precision figure can hide an alias that is wrong every time.

The same criterion selects 24 further aliases across 18 other entities. Those are reported
and NOT applied: the owner's decision names this concept, and withdrawing an alias has a
measured blast radius beyond its own concept, below.

WHY THE PLAN COVERS TWO LAYERS AND A CAP
========================================

``MENTIONS_ENTITY`` stores ``matched_aliases``, so its dependence is readable off the edge.
``ABOUT_CONCEPT`` does not, and its stored evidence quote is a window round the match
rather than the whole verse, so an edge that looks alias-dependent may rest on a surviving
alias the window does not show. That layer is therefore re-derived over the corpus twice,
once with the three forms present and once withdrawn, and the difference is the answer.

Re-derivation surfaced a consequence worth naming. ``assign_concepts`` caps a passage at
``MAX_CONCEPTS_PER_PASSAGE`` concepts and breaks ties on **how many passages each concept
is attested on corpus-wide**. Withdrawing three aliases lowers SOMA-PRESSING's corpus-wide
attestation, which changes that tie-break, which reshuffles which concepts survive the cap
on passages that contain no soma alias at all. The reshuffle is deterministic and
reproducible, not a bug -- but it changes concepts the owner's decision did not name, so it
is reported as its own correction rather than folded into this one.

Nothing here is written. The script emits the plan and its proof.

Usage:
    python scripts/wave3_soma_pressing_correction.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.enrich.concepts import (
    assign_concepts,
    load_concepts,
    load_non_triggering_aliases,
)
from vedagraph.enrich.corpus import load_corpus
from vedagraph.enrich.guards import MAX_CONCEPTS_PER_PASSAGE

ROOT = pathlib.Path(".")
TARGET = "VG:CONCEPT:SOMA-PRESSING"
QUALITY_PROOF = pathlib.Path("data/staging/quality/proofs/alias_soundness.json")
OUT = pathlib.Path("data/staging/integration/wave3_soma_pressing_correction.json")

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: The five senses the owner forbids conflating. Each must be a distinct graph entity, and
#: no Sanskrit alias may be shared between any two of them -- a shared surface is how a
#: conflation happens without anyone deciding to make one.
SOMA_SENSES: tuple[tuple[str, str], ...] = (
    ("VG:CONCEPT:SOMA-DRINK", "the substance and the drink pressed from it"),
    ("VG:CONCEPT:SOMA-PRESSING", "the pressing rite and occasion"),
    ("VG:CONCEPT:GRAHA-SOMA-DRAWING", "the drawing of a soma portion"),
    ("VG:DEVATA:SOMAH", "the deity"),
    ("VG:DEVATA:PAVAMANAH-SOMAH", "the deity in his self-purifying cult form"),
)


def load_quality_rows() -> list[dict[str, Any]]:
    if not QUALITY_PROOF.exists():
        return []
    data = json.loads(QUALITY_PROOF.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = data.get("rows") or []
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    declared = load_non_triggering_aliases(ROOT)
    retired = tuple(sorted(alias for cid, kind, alias in declared if cid == TARGET))
    if not retired:
        print("  no non-triggering alias is declared for", TARGET)
        return 1

    # The measurement the retirement rests on, read back from the artifact rather than
    # restated, so the criterion and the withdrawal cannot drift apart.
    quality = load_quality_rows()
    evidence = {
        row["alias"]: {
            "treebank_occurrences": row["treebank_occurrences"],
            "dominant_human_lemma": row["dominant_human_lemma"],
            "dominant_share": row["dominant_share"],
            "human_lemmas_observed": row["human_lemmas_observed"],
            "h2_verdict": row["h2_verdict"],
        }
        for row in quality
        if row.get("entity_key") == TARGET
    }
    unmeasured = [alias for alias in retired if alias not in evidence]
    not_ambiguous = [
        alias
        for alias in retired
        if evidence.get(alias, {}).get("h2_verdict") != "AMBIGUOUS_SURFACE"
    ]

    # The same criterion elsewhere: reported, not applied.
    elsewhere = collections.defaultdict(list)
    for row in quality:
        if row["h2_verdict"] == "AMBIGUOUS_SURFACE" and row["entity_key"] != TARGET:
            elsewhere[row["entity_key"]].append(
                {"alias": row["alias"], "dominant_share": row["dominant_share"]}
            )

    # ---- layer 1: MENTIONS_ENTITY, readable off the edge -----------------------------
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            stored = session.run(
                "MATCH (p)-[r:MENTIONS_ENTITY]->(c) WHERE c.entity_key = $key "
                "RETURN p.canonical_key AS key, r.matched_aliases AS aliases, "
                "r.mention_id AS mention_id",
                key=TARGET,
            ).data()
            senses = session.run(
                "UNWIND $keys AS k MATCH (n {entity_key: k}) "
                "RETURN k AS key, labels(n) AS labels, n.aliases_sa AS aliases_sa",
                keys=[key for key, _why in SOMA_SENSES],
            ).data()
    finally:
        driver.close()

    retired_set = set(retired)
    mentions_retire: list[dict[str, Any]] = []
    mentions_edit: list[dict[str, Any]] = []
    for edge in stored:
        aliases = set(edge["aliases"] or [])
        if not aliases or not aliases & retired_set:
            continue
        if aliases <= retired_set:
            mentions_retire.append(
                {"canonical_key": edge["key"], "matched_aliases": sorted(aliases)}
            )
        else:
            mentions_edit.append(
                {
                    "canonical_key": edge["key"],
                    "matched_aliases_before": sorted(aliases),
                    "matched_aliases_after": sorted(aliases - retired_set),
                }
            )

    # ---- layer 2: ABOUT_CONCEPT, re-derived over the corpus ---------------------------
    corpus = load_corpus(ROOT)
    after_rows = load_concepts(ROOT)
    before_rows = tuple(
        dataclasses.replace(
            row,
            aliases_sa=tuple(sorted(set(row.aliases_sa) | retired_set)),
            non_triggering_aliases_sa=(),
        )
        if row.concept_id == TARGET
        else row
        for row in after_rows
    )

    def derive(rows: tuple[Any, ...]) -> set[tuple[str, str, str]]:
        assertions, _report = assign_concepts(corpus, rows)
        return {(a.passage_key, a.concept_id, a.provenance.method) for a in assertions}

    before = derive(before_rows)
    after = derive(after_rows)

    target_before = {x for x in before if x[1] == TARGET}
    target_after = {x for x in after if x[1] == TARGET}
    lost = sorted(target_before - target_after)
    gained = sorted(target_after - target_before)
    lost_keys = {k for k, _c, _m in lost}
    gained_keys = {k for k, _c, _m in gained}
    kept_keys = {k for k, _c, _m in target_after}

    # A passage in both lost and gained changed its method string, not its existence: the
    # Sanskrit half of a mixed-evidence assertion was a retired alias, so the assertion
    # survives on the English one and the method narrows. That is an update, not a create.
    method_narrowed = sorted(gained_keys & lost_keys)
    truly_new = sorted(gained_keys - lost_keys)
    truly_retired = sorted(lost_keys - kept_keys)

    # ---- the collateral the cap's global tie-break causes -----------------------------
    collateral_lost = sorted(x for x in before - after if x[1] != TARGET)
    collateral_gained = sorted(x for x in after - before if x[1] != TARGET)
    collateral_concepts = sorted(
        {x[1] for x in collateral_lost} | {x[1] for x in collateral_gained}
    )

    # ---- the conflation guard ---------------------------------------------------------
    sense_rows = {row.concept_id: row for row in after_rows}
    sense_report = []
    overlaps: list[str] = []
    for key, why in SOMA_SENSES:
        graph_row = next((s for s in senses if s["key"] == key), None)
        concept = sense_rows.get(key)
        sense_report.append(
            {
                "entity_key": key,
                "sense": why,
                "present_in_graph": graph_row is not None,
                "graph_labels": (graph_row or {}).get("labels"),
                "registry_alias_count": len(concept.aliases_sa) if concept else None,
            }
        )
    for i, (left, _wl) in enumerate(SOMA_SENSES):
        for right, _wr in SOMA_SENSES[i + 1 :]:
            a = sense_rows.get(left)
            b = sense_rows.get(right)
            if a is None or b is None:
                continue
            shared = sorted(set(a.aliases_sa) & set(b.aliases_sa))
            if shared:
                overlaps.append(f"{left} and {right} share Sanskrit alias(es) {shared}")

    findings: list[str] = []
    if unmeasured:
        findings.append(f"retired without a soundness measurement: {unmeasured}")
    if not_ambiguous:
        findings.append(f"retired but not AMBIGUOUS_SURFACE: {not_ambiguous}")
    if overlaps:
        findings.extend(overlaps)
    absent = [s["entity_key"] for s in sense_report if not s["present_in_graph"]]
    if absent:
        findings.append(f"a distinguished soma sense is not in the graph: {absent}")

    report = {
        "schema_version": "1.0",
        "owner_decision": (
            "section 3 -- SOMA-PRESSING stays as a canonical ritual object; its weak "
            "lexical aliases lose assertion authority"
        ),
        "mode": "PLAN_NO_WRITE",
        "concept": TARGET,
        "concept_retained": True,
        "retired_aliases": list(retired),
        "retirement_status": "NON_TRIGGERING_ALIAS",
        "retirement_criterion": (
            "h2_verdict = AMBIGUOUS_SURFACE in data/staging/quality/proofs/"
            "alias_soundness.json: the alias's dominant human lemma holds under 80% of its "
            "occurrences in a published human treebank"
        ),
        "retained_for": ["search", "candidate generation", "audit", "manual review"],
        "may_no_longer_create": ["MENTIONS_ENTITY", "ABOUT_CONCEPT", "ritual identity"],
        "measurement_per_alias": evidence,
        "surviving_trigger_aliases": len(sense_rows[TARGET].aliases_sa),
        "mentions_entity": {
            "edges_on_the_concept": len(stored),
            "retire_sole_evidence_is_retired": len(mentions_retire),
            "update_drop_retired_alias_keep_edge": len(mentions_edit),
            "untouched": len(stored) - len(mentions_retire) - len(mentions_edit),
            "retire_keys": [row["canonical_key"] for row in mentions_retire],
            "update_rows": mentions_edit,
        },
        "about_concept": {
            "method": "re-derived over all 20,210 mantras with and without the three aliases",
            "assertions_before": len(target_before),
            "assertions_after": len(target_after),
            "retire": len(truly_retired),
            "update_method_narrowed_to_english_only": len(method_narrowed),
            "create_newly_attested": len(truly_new),
            "retire_keys": truly_retired,
            "method_narrowed_keys": method_narrowed,
            "newly_attested_keys": truly_new,
            "passages_keeping_the_concept_on_other_evidence": len(lost_keys & kept_keys),
        },
        "collateral_from_the_per_passage_cap": {
            "finding": (
                f"assign_concepts caps a passage at MAX_CONCEPTS_PER_PASSAGE="
                f"{MAX_CONCEPTS_PER_PASSAGE} and breaks ties on each concept's corpus-wide "
                "attestation count. Withdrawing three aliases lowers SOMA-PRESSING's count, "
                "which reshuffles the cap on passages containing no soma alias at all. "
                "Deterministic and reproducible, and outside the decision the owner took."
            ),
            "other_concepts_affected": collateral_concepts,
            "assertions_lost_elsewhere": len(collateral_lost),
            "assertions_gained_elsewhere": len(collateral_gained),
            "lost_elsewhere": [list(x) for x in collateral_lost],
            "gained_elsewhere": [list(x) for x in collateral_gained],
            "whole_layer_before": len(before),
            "whole_layer_after": len(after),
            "whole_layer_net": len(after) - len(before),
            "requires_its_own_decision": True,
        },
        "same_criterion_elsewhere_reported_not_applied": {
            "entities": len(elsewhere),
            "aliases": sum(len(v) for v in elsewhere.values()),
            "detail": {k: v for k, v in sorted(elsewhere.items())},
        },
        "conflation_guard": {
            "senses_held_apart": sense_report,
            "shared_sanskrit_aliases_between_senses": overlaps,
        },
        "findings": findings,
        "verdict": "PLAN_READY" if not findings else "DEFECT",
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  SOMA-PRESSING WEAK-ALIAS CORRECTION -- plan only, nothing written")
    print()
    print(f"  concept retained: {TARGET}")
    print(f"  retired to NON_TRIGGERING_ALIAS: {', '.join(retired)}")
    print(f"  surviving trigger aliases: {report['surviving_trigger_aliases']}")
    print()
    mentions = report["mentions_entity"]
    print(f"  MENTIONS_ENTITY  ({mentions['edges_on_the_concept']} edges on the concept)")
    print(f"    retire, sole evidence retired : {mentions['retire_sole_evidence_is_retired']:>5}")
    kept = mentions["update_drop_retired_alias_keep_edge"]
    print(f"    update, drop the alias, keep  : {kept:>5}")
    print(f"    untouched                     : {mentions['untouched']:>5}")
    about = report["about_concept"]
    print()
    print(f"  ABOUT_CONCEPT    ({about['assertions_before']} -> {about['assertions_after']})")
    print(f"    retire                        : {about['retire']:>5}")
    narrowed = about["update_method_narrowed_to_english_only"]
    print(f"    update, method narrowed       : {narrowed:>5}")
    print(f"    create, newly attested        : {about['create_newly_attested']:>5}")
    collateral = report["collateral_from_the_per_passage_cap"]
    print()
    print("  COLLATERAL from the per-passage cap's global tie-break")
    print(f"    other concepts affected       : {len(collateral['other_concepts_affected'])}")
    print(f"    lost elsewhere                : {collateral['assertions_lost_elsewhere']:>5}")
    print(f"    gained elsewhere              : {collateral['assertions_gained_elsewhere']:>5}")
    print(
        f"    whole layer                   : {collateral['whole_layer_before']:,} -> "
        f"{collateral['whole_layer_after']:,} ({collateral['whole_layer_net']:+})"
    )
    print("    -> held as a separate correction; it changes concepts the decision did not name")
    print()
    same = report["same_criterion_elsewhere_reported_not_applied"]
    print(
        f"  same criterion elsewhere: {same['aliases']} aliases on {same['entities']} entities, "
        "reported and NOT applied"
    )
    print()
    print("  conflation guard, five senses held apart:")
    for sense in sense_report:
        mark = "ok " if sense["present_in_graph"] else "MISSING"
        print(f"    {mark} {sense['entity_key']:34}{sense['sense']}")
    print()
    if findings:
        print(f"  {len(findings)} FINDING(S):")
        for finding in findings:
            print(f"    - {finding}")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    print()
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
