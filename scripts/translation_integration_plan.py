#!/usr/bin/env python3
"""Phase F and G: the immutable import plan every later phase reads.

One plan, written once, consumed by the dry run, the executor and the readback. The reason
it is a file and not three code paths is a defect this campaign has already paid for: a
readback that derives its own expectation by querying the graph will confirm whatever the
importer did, including the wrong thing. So the promise is written down first, hashed, and
the executor and the verifier both read the same bytes.

**A row is not a node.** Griffith prints one Atharvavedic rendering across two of this
corpus's verses, and staging wrote that as two rows carrying the same literal. Importing
both would be the "separate fake 1:1 translations" the owner forbade, so 68 range rows
collapse into 34 :class:`Translation` nodes on the model M13 established for the Rigveda:
the node anchors on the lower verse and enumerates its whole span in
``covers_canonical_keys``. Every count below therefore says whether it counts rows, nodes
or covered verses, because for this population those are 68, 34 and 68.

**The language correction is an overlay, not an edit.** ``rows.jsonl`` is hashed in the
staging manifest and every Gate B/C finding was computed against those bytes. Correcting
24 rows in place would silently invalidate the evidence the import rests on, so the
correction lives here and the staged artifact stays byte-identical.

Run:  python scripts/translation_integration_plan.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import sys
from typing import Any, Final

import translation_integration_common as T

#: Written onto every node this round creates, so the population is selectable later
#: without reconstructing the plan.
IMPORT_BATCH: Final = "TRANSLATION_BULK_2026_09_16"

QUALITY_STATUS: Final = "MACHINE_ALIGNED"
RIGHTS_STATUS: Final = "PUBLIC_DOMAIN"

#: Citation prefixes per Veda, for rendering a reused-from key as a human citation.
_CITATION: Final[dict[str, str]] = {"RV": "RV", "SV": "SV", "YV": "VS", "AV": "AVS"}


def citation_for(canonical_key: str) -> str:
    """``VG:RV:SAK:M03:S040:V009`` -> ``RV 3.40.9``.

    Built from the key rather than read from the node, because the plan has to be
    constructible without a database: the dry run compares it against the graph, and a
    plan that needed the graph to exist could not be that comparison's other side.
    """
    parts = canonical_key.split(":")
    veda = parts[1] if len(parts) > 1 else "?"
    numbers = [segment.lstrip("MSVKAPRD").lstrip("0") or "0" for segment in parts[3:]]
    return f"{_CITATION.get(veda, veda)} {'.'.join(numbers)}"


def translation_id_for(canonical_key: str, source_id: str) -> str:
    """A deterministic id, so a re-run of the plan names the same nodes.

    ``translation_id`` carries a uniqueness constraint. Deriving it from the anchor key and
    the source means a second dry run cannot propose a colliding node, and an interrupted
    execution can be re-run without creating a duplicate beside the one that landed.
    """
    seed = f"vedagraph:translation:{canonical_key}:{source_id}:{IMPORT_BATCH}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-5{digest[13:16]}-{digest[16:20]}-{digest[20:32]}"


def build(packet: dict[str, Any], classified: dict[str, dict[str, Any]]) -> dict[str, Any]:
    importable = [r for r in classified.values() if r["importable"]]

    # -- group the range rows by their print unit -----------------------------------
    # The locator is the print unit's identity, and every row sharing one carries the same
    # literal, which Gate B verified. Grouping on it is what turns 68 rows into 34 nodes.
    range_groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in importable:
        if row["final_class"] == "IMPORT_MANTRA_RANGE":
            range_groups[row["source_locator"]].append(row)

    nodes: list[dict[str, Any]] = []
    row_to_node: dict[str, str] = {}

    for row in sorted(importable, key=lambda r: r["row_id"]):
        if row["final_class"] == "IMPORT_MANTRA_RANGE":
            continue
        nodes.append(_node_for(packet, row, [row], row["canonical_key"]))

    for locator in sorted(range_groups):
        group = sorted(range_groups[locator], key=lambda r: r["canonical_key"])
        anchor = group[0]["canonical_key"]
        nodes.append(_node_for(packet, group[0], group, anchor))

    for node in nodes:
        for row_id in node["staged_row_ids"]:
            row_to_node[row_id] = node["translation_id"]

    _assert_plan_is_coherent(importable, nodes)
    return _report(packet, classified, importable, nodes, row_to_node)


def _node_for(
    packet: dict[str, Any],
    lead: dict[str, Any],
    group: list[dict[str, Any]],
    anchor: str,
) -> dict[str, Any]:
    """One :class:`Translation` node, with every property the plan promises to write."""
    staged = packet["staged"][lead["row_id"]]
    payload = staged["payload"]
    final = lead["final_class"]
    covered = sorted({row["canonical_key"] for row in group})

    is_range = final == "IMPORT_MANTRA_RANGE"
    is_reuse = final == "IMPORT_REUSED_RENDERING"

    node: dict[str, Any] = {
        "translation_id": translation_id_for(anchor, staged["source_id"]),
        "attach_to_canonical_key": anchor,
        "veda": lead["veda"],
        "final_class": final,
        "staged_row_ids": sorted(row["row_id"] for row in group),
        "covers_canonical_keys": covered,
        "properties": {
            "text": payload["text"],
            "translator": payload["translator"],
            "work_edition": payload["work_edition"],
            "year": payload.get("year"),
            # The overlay. The staged payload says "en" on every row; the 24 Latin rows
            # carry their measured language instead, and rows.jsonl is left untouched.
            "language": lead["import_language"],
            "quality_status": QUALITY_STATUS,
            "rights_status": RIGHTS_STATUS,
            "source_id": staged["source_id"],
            "source_locator": staged["source_locator"],
            "alignment_level": "MANTRA_RANGE" if is_range else "MANTRA",
            "import_batch": IMPORT_BATCH,
        },
    }
    props = node["properties"]

    if staged.get("source_url"):
        props["source_url"] = staged["source_url"]
    if payload.get("snapshot_sha256"):
        props["snapshot_sha256"] = payload["snapshot_sha256"]

    if is_range:
        # The complete span, enumerated. A MANTRA_RANGE node that names one verse is
        # indistinguishable from a dedicated translation, so the API model refuses it.
        props["covers_canonical_keys"] = covered
        props["source_unit"] = str(payload.get("printed_span") or "")
        props["source_verse_spine"] = "PRINTED_MULTI_VERSE_UNIT"
    else:
        props["covers_canonical_keys"] = [anchor]

    if is_reuse:
        source_key = payload["cross_corpus_source_key"]
        props["reuse_kind"] = "REUSED_RENDERING"
        props["reused_from_veda"] = source_key.split(":")[1]
        props["reused_from_passage_key"] = source_key
        props["reused_from_citation"] = citation_for(source_key)
        props["reuse_basis"] = staged["mapping_method"]
        props["reuse_sanskrit_similarity"] = payload.get("sanskrit_similarity")
        props["reuse_relation_asserted"] = payload.get("relation_asserted")
        # The source translation's own identity, read from the graph while the plan is
        # built and then frozen into it. Resolved here rather than by the executor because
        # the owner policy requires "source translation identity" in the provenance, and a
        # field the executor fills is a field the readback cannot check against a promise.
        props["reused_from_translation_id"] = _source_translation_ids()[source_key]

    if lead["final_class"] == "IMPORT_VERIFIED_FORCED_ADDRESS":
        props["address_verification"] = "INDEPENDENTLY_VERIFIED_AGAINST_PRINTED_SOURCE"
        props["owner_decision"] = "OWNER_DECISION_C_FORCED_ADDRESSES"

    if lead["final_class"] == "IMPORT_NON_ENGLISH_TRANSLATION":
        props["language_correction"] = (
            "staged as 'en'; the literal is Griffith's Latin substitution, verified "
            "against the pinned source page"
        )

    return node


_SOURCE_TRANSLATION_IDS: dict[str, str] | None = None


def _source_translation_ids() -> dict[str, str]:
    """``canonical_key -> translation_id`` for every Rigvedic translation, read once.

    Read from the graph because that is where the identity lives: the reused rendering is a
    particular node's text, and "Griffith's Rigveda" is an edition rather than an identity.
    A key with no translation raises through the ``KeyError`` at the call site, which is
    correct -- a reuse row whose source carries no translation has nothing to reuse.
    """
    global _SOURCE_TRANSLATION_IDS
    if _SOURCE_TRANSLATION_IDS is None:
        import gate_bc_common as G

        driver = G.driver()
        try:
            with G.session(driver) as session:
                _SOURCE_TRANSLATION_IDS = {
                    record["k"]: record["t"]
                    for record in session.run(
                        """
                        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                        WHERE t.translation_id IS NOT NULL
                        RETURN m.canonical_key AS k, t.translation_id AS t
                        """
                    )
                }
        finally:
            driver.close()
    return _SOURCE_TRANSLATION_IDS


def _assert_plan_is_coherent(importable: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> None:
    """Refuse a plan that could not be executed truthfully."""
    covered_rows = [row_id for node in nodes for row_id in node["staged_row_ids"]]
    if len(covered_rows) != len(set(covered_rows)):
        raise T.AccountingError("a staged row appears in more than one planned node")
    if set(covered_rows) != {row["row_id"] for row in importable}:
        missing = {row["row_id"] for row in importable} - set(covered_rows)
        raise T.AccountingError(f"{len(missing)} importable rows reach no planned node")

    ids = [node["translation_id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise T.AccountingError("two planned nodes share a translation_id")

    # No canonical key may be claimed twice. It is the check that would have caught
    # importing both halves of a print unit as separate translations.
    claims = collections.Counter(key for node in nodes for key in node["covers_canonical_keys"])
    twice = {key: n for key, n in claims.items() if n > 1}
    if twice:
        raise T.AccountingError(f"{len(twice)} canonical keys are claimed by two nodes: {twice}")

    for node in nodes:
        props = node["properties"]
        if props["alignment_level"] == "MANTRA_RANGE" and len(node["covers_canonical_keys"]) < 2:
            raise T.AccountingError(f"{node['translation_id']} claims MANTRA_RANGE over one verse")
        if props["alignment_level"] != "MANTRA_RANGE" and len(node["covers_canonical_keys"]) != 1:
            raise T.AccountingError(
                f"{node['translation_id']} is not a range but covers "
                f"{len(node['covers_canonical_keys'])} verses"
            )
        if props.get("reuse_kind") and not props.get("reused_from_passage_key"):
            raise T.AccountingError(f"{node['translation_id']} declares reuse without a source")
        if props.get("reuse_kind") and not props.get("reused_from_translation_id"):
            raise T.AccountingError(
                f"{node['translation_id']} declares reuse without naming the translation "
                "it reuses; the owner policy requires the source translation identity"
            )
        if node["attach_to_canonical_key"] not in node["covers_canonical_keys"]:
            raise T.AccountingError(f"{node['translation_id']} is not inside its own span")


def _report(
    packet: dict[str, Any],
    classified: dict[str, dict[str, Any]],
    importable: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    row_to_node: dict[str, str],
) -> dict[str, Any]:
    def count(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
        return dict(sorted(collections.Counter(r[field] for r in rows).items()))

    independent = [
        n
        for n in nodes
        if n["final_class"] in T.INDEPENDENT_ENGLISH_CLASSES and n["properties"]["language"] == "en"
    ]
    reused = [n for n in nodes if n["properties"].get("reuse_kind")]
    ranges = [n for n in nodes if n["properties"]["alignment_level"] == "MANTRA_RANGE"]
    non_english = [n for n in nodes if n["properties"]["language"] != "en"]
    forced = [n for n in nodes if n["final_class"] == "IMPORT_VERIFIED_FORCED_ADDRESS"]

    # -- predicted post-import coverage, per Veda, per population -------------------
    from vedagraph.domain import layer_figures

    predicted = {}
    for veda in ("RV", "SV", "YV", "AV"):
        corpus = layer_figures.CORPUS_MANTRAS[veda]
        before_dedicated = layer_figures.DEDICATED_ENGLISH_MANTRAS[veda]
        before_range = layer_figures.RANGE_COVERED_MANTRAS[veda]
        before_reused = layer_figures.REUSED_RENDERING_MANTRAS[veda]
        before_other = layer_figures.NON_ENGLISH_MANTRAS[veda]

        add_dedicated = len(
            [
                n
                for n in nodes
                if n["veda"] == veda
                and n["final_class"] in ("IMPORT_SOURCE_EXPLICIT", "IMPORT_VERIFIED_FORCED_ADDRESS")
            ]
        )
        # Ranges add covered verses, not nodes: 34 nodes reach 68 verses.
        add_range = len(
            [k for n in ranges if n["veda"] == veda for k in n["covers_canonical_keys"]]
        )
        add_reused = len([n for n in reused if n["veda"] == veda])
        add_other = len([n for n in non_english if n["veda"] == veda])

        dedicated = before_dedicated + add_dedicated
        range_covered = before_range + add_range
        reused_after = before_reused + add_reused
        other = before_other + add_other
        predicted[veda] = {
            "corpus_mantras": corpus,
            "dedicated_translations": dedicated,
            "range_covered_verses": range_covered,
            "reused_rendering_verses": reused_after,
            "other_language_verses": other,
            "uncovered_verses": corpus - dedicated - range_covered - reused_after - other,
            "added_this_round": {
                "dedicated": add_dedicated,
                "range_covered_verses": add_range,
                "reused_rendering": add_reused,
                "other_language": add_other,
            },
        }

    return {
        "plan_version": 1,
        "import_batch": IMPORT_BATCH,
        "phase": "F-G",
        "staged_rows_total": T.EXPECTED_ROWS,
        "terminal_classes": T.class_counts(classified),
        "eligibility_rule": (
            "evidence-safe AND product-representable AND policy-approved AND not already "
            "canonical AND not conflicting. Each conjunct is measured separately below so "
            "a row excluded for one reason cannot be reported as excluded for another."
        ),
        "rows": {
            "importable": len(importable),
            "by_veda": count(importable, "veda"),
            "by_source": count(importable, "source_id"),
            "by_final_class": count(importable, "final_class"),
            "by_language": count(importable, "import_language"),
            "withheld_or_rejected": T.EXPECTED_ROWS - len(importable),
        },
        "nodes": {
            "total": len(nodes),
            "why_fewer_than_rows": (
                f"{len(importable)} rows produce {len(nodes)} nodes because "
                f"{len([n for n in ranges if len(n['staged_row_ids']) > 1])} print units "
                "were staged once per covered verse. Importing a node per row would create "
                "the duplicated 1:1 translations the owner forbade."
            ),
            "by_veda": dict(sorted(collections.Counter(n["veda"] for n in nodes).items())),
            "by_final_class": dict(
                sorted(collections.Counter(n["final_class"] for n in nodes).items())
            ),
            "by_source": dict(
                sorted(collections.Counter(n["properties"]["source_id"] for n in nodes).items())
            ),
            "by_language": dict(
                sorted(collections.Counter(n["properties"]["language"] for n in nodes).items())
            ),
            "by_alignment_level": dict(
                sorted(
                    collections.Counter(n["properties"]["alignment_level"] for n in nodes).items()
                )
            ),
            "independent_english": len(independent),
            "reused_renderings": len(reused),
            "mantra_range": len(ranges),
            "non_english": len(non_english),
            "verified_forced_address": len(forced),
        },
        "relationships": {
            "HAS_TRANSLATION": len(nodes),
            "note": (
                "one edge per node, anchored on one verse. A range node deliberately does "
                "not create an edge from every verse it covers: the span lives in "
                "covers_canonical_keys, and edges from all of them would make the range "
                "indistinguishable from 68 dedicated translations."
            ),
        },
        "canonical_verses_reached": {
            "total": len({k for n in nodes for k in n["covers_canonical_keys"]}),
            "by_veda": dict(
                sorted(
                    collections.Counter(
                        k.split(":")[1] for n in nodes for k in n["covers_canonical_keys"]
                    ).items()
                )
            ),
        },
        "properties_written": sorted({k for n in nodes for k in n["properties"]}),
        "owner_decisions_applied": {
            "OWNER_DECISION_A_RV_SPAN": (
                "CLOSE. No rows are imported for RV 1.65-1.70: M13 already resolved the "
                "span, and the 30 paired verses are covered by its MANTRA_RANGE nodes, "
                "which the product now represents."
            ),
            "OWNER_DECISION_C_FORCED_ADDRESSES": {
                "approved": len(forced),
                "withheld_by_name": sorted(T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS),
                "withheld_keys_absent_from_plan": sorted(
                    key
                    for key in T.OWNER_WITHHELD_FORCED_ADDRESS_KEYS
                    if key not in {k for n in nodes for k in n["covers_canonical_keys"]}
                ),
            },
            "REUSED_RENDERING_POLICY": {
                "nodes": len(reused),
                "all_disclose_reuse": all(
                    n["properties"].get("reuse_kind") == "REUSED_RENDERING"
                    and n["properties"].get("reused_from_passage_key")
                    for n in reused
                ),
                "counted_as_independent_english": len([n for n in reused if n in independent]),
            },
            "LATIN_SUBSTITUTION_POLICY": {
                "nodes": len(non_english),
                "language": sorted({n["properties"]["language"] for n in non_english}),
                "counted_as_independent_english": len([n for n in non_english if n in independent]),
                "owner_quoted_population": 22,
                "measured_population": len(non_english),
                "discrepancy_note": (
                    "The owner decision quotes 22, which is what Gate C measured. Two more "
                    "rows carry Latin literals and were classified as source-explicit "
                    "English: AV 20.136.1 and RV 10.61.6. Both are verified against the "
                    "pinned source pages and both are imported as Latin, because the "
                    "decision's operative clause is that a Latin row must never increase "
                    "English coverage."
                )
                if len(non_english) != 22
                else "measured population equals the owner's figure",
            },
        },
        "predicted_coverage_after_import": predicted,
        "invariants_the_migration_must_hold": {
            "core_corpus_unchanged": {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839},
            "nodes_created": len(nodes),
            "relationships_created": len(nodes),
            "existing_translations_modified": 0,
            "mantra_nodes_modified": 0,
            "text_versions_modified": 0,
        },
        "row_to_node": row_to_node,
        "nodes_detail": sorted(nodes, key=lambda n: n["attach_to_canonical_key"]),
    }


def main() -> int:
    packet = T.load_packet()
    classified = T.classify(packet)
    T.assert_one_disposition(classified)
    plan = build(packet, classified)

    path = T.write_json(T.INTEGRATION / "translation_import_plan.json", plan)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    T.write_json(
        T.INTEGRATION / "translation_import_plan.sha256.json",
        {
            "path": "data/staging/translation/integration/translation_import_plan.json",
            "sha256": digest,
            "bytes": path.stat().st_size,
            "note": (
                "the dry run, the executor and the readback all verify this digest before "
                "reading the plan, so none of them can be running against a different one"
            ),
        },
    )

    print("rows importable        :", plan["rows"]["importable"], plan["rows"]["by_veda"])
    print("nodes to create        :", plan["nodes"]["total"], plan["nodes"]["by_veda"])
    print("edges to create        :", plan["relationships"]["HAS_TRANSLATION"])
    print("verses reached         :", plan["canonical_verses_reached"])
    print("by final class (nodes) :", json.dumps(plan["nodes"]["by_final_class"]))
    print("by alignment level     :", json.dumps(plan["nodes"]["by_alignment_level"]))
    print("by language            :", json.dumps(plan["nodes"]["by_language"]))
    print("independent english    :", plan["nodes"]["independent_english"])
    print("reused renderings      :", plan["nodes"]["reused_renderings"])
    print("non english            :", plan["nodes"]["non_english"])
    print("forced address         :", plan["nodes"]["verified_forced_address"])
    print()
    print("predicted coverage after import:")
    for veda, row in plan["predicted_coverage_after_import"].items():
        print(
            f"  {veda}  corpus={row['corpus_mantras']:>6}"
            f"  dedicated={row['dedicated_translations']:>6}"
            f"  range={row['range_covered_verses']:>4}"
            f"  reused={row['reused_rendering_verses']:>4}"
            f"  other_lang={row['other_language_verses']:>3}"
            f"  uncovered={row['uncovered_verses']:>5}"
        )
    print()
    print("plan sha256:", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
