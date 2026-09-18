#!/usr/bin/env python3
"""Stage four R4 closures whose evidence is already held: RITUAL-004, ENTITY-007,
COMMUNITIES-002 and TRANSLATION-004.

One script because they share nothing but the discipline: every row written here is derived
from something the repository already states, every absence that cannot be filled is typed
in the row with its reason, and nothing is written to the graph -- the migration applies it.

GAP-RITUAL-004 -- two officiants nobody classified
==================================================

``:RitualRole`` holds 20 nodes. 14 carry ``in_classical_sixteen: true``, 4 carry ``false``,
and **2 carry null**: ``VG:CONCEPT:AGNIDH-FIRE-KINDLER`` and ``VG:CONCEPT:POTR-PURIFIER``.
Both are members of the classical sixteen -- the agnīdh kindles the fire and the potṛ is one
of the four Brahman-side priests -- so the nulls were a missing classification, not a
judgement that they are outside the schema. Typing them takes the flagged set from 14 to
**16**, which is what "RitualRole holds the classical sixteen" asks for, and removes the
other open half: a reader can no longer confuse a non-member with an unclassified row.

A second defect is fixed with them. ``denominator_schema`` carries two different KINDS of
value -- 9 rows hold the schema identifier ``SRAUTASUTRA_RTVIJ_SCHEMA_OF_SIXTEEN`` and 9
hold a whole prose sentence about it. A field that is sometimes an identifier and sometimes
a paragraph cannot be grouped on, so the identifier is written to every row and the prose
moves to ``denominator_schema_note``.

GAP-ENTITY_COVERAGE-007 -- personification, typed as a refusal or as unattempted
===============================================================================

13 ``:NaturalPhenomenon`` nodes, **0** carrying any personification status, and the property
did not exist -- so an unresolved entity could not be told apart from a refused one, which
is the ambiguity this project forbids everywhere else.

Personification is an **interpretive** relation and is not minted as identity here. No
``:Personification`` node is created and no ``PERSONIFIES`` edge is asserted. What lands is
a status on the phenomenon, from a closed vocabulary, decided by evidence the graph already
holds: a phenomenon is ``PERSONIFIED_AS_A_REGISTERED_DEVATA`` only where a ``:Devata``
carrying the same Sanskrit stem exists, and the deity key is recorded beside it.
``REFUSED_NO_REGISTERED_DEITY_COUNTERPART`` is the typed refusal, and it is a statement
about this graph's registry rather than about the Vedas.

GAP-COMMUNITIES-002 -- and a correction to the figure R3 reported
=================================================================

R3 recorded "24 PAIRs are mechanical decomposition over ``devata_components.yaml``". That is
not what the file supports. Measured: ``devata_components.yaml`` declares **20** composites,
**14** of them are already landed as 28 ``COMPOSED_OF`` edges, and only **6** remain
unlanded -- ``ADITYAH``, ``DYAVAPRTHIVYAU``, ``INDRAVARUNAU``, ``MARUTAH``, ``USASANAKTA``,
``VISVEDEVAH``. The other 51 undecomposed composites have no entry in the registry at all,
so decomposing them is new curation and not mechanical work.

So this stages the 6 the registry supports, and types the remaining 51 with the reason they
are not enumerable from anything held -- which is the second arm of the closure test for
groups, and is the honest answer for the pairs too rather than leaving them looking
unfinished.

GAP-TRANSLATION-004 -- coverage the measure cannot see
======================================================

36 Rigvedic mantras carry no ``HAS_TRANSLATION`` edge. 34 of them are **not untranslated**:
Griffith merged a verse pair into one printed unit, so the rendering sits on the anchor verse
and the covered verse has no edge of its own. 30 were already identified and their anchors
typed ``alignment_level: MANTRA_RANGE``; the other 4 --
``VG:RV:SAK:M05:S055:V008``, ``VG:RV:SAK:M09:S007:V009``, ``VG:RV:SAK:M10:S048:V007`` and
``VG:RV:SAK:M10:S132:V005`` -- have an anchor whose printed unit carries 4 lines where every
other unit in the hymn carries 2 or 3, and whose rendering is still typed ``MANTRA``.

Two things are staged. The 4 anchors are re-typed ``MANTRA_RANGE``, which is the correction
already applied to the 30 and is not a split of Griffith's prose -- splitting it would
fabricate. And each of the 34 covered verses gains a ``HAS_TRANSLATION`` edge to **the
anchor's existing** ``:Translation`` node, carrying ``alignment_level: MANTRA_RANGE`` and the
anchor it shares. No new translation text is created; the covered verse simply becomes able
to reach the rendering that covers it, which is what "covered" has to mean if the coverage
is to be true of the verse rather than only of a report.

``VG:RV:SAK:M10:S086:V016`` and ``VG:RV:SAK:M10:S086:V017`` are confirmed absent from the
only ingested source and are typed as such. They are not given an edge.

Usage:
    python scripts/r4_stage_combined.py
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import sys
from typing import Any, Final

import yaml
from neo4j import GraphDatabase, Query

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "combined"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"
TIMEOUT: Final[float] = 300.0

CLASSICAL_SCHEMA: Final = "SRAUTASUTRA_RTVIJ_SCHEMA_OF_SIXTEEN"

#: The two nulls, with why each is a member. Named individually rather than filled by a
#: sweep, because "classify the nulls" and "classify these two officiants" are different
#: acts and only the second can be checked.
RITUAL_ROLE_RULINGS: Final[dict[str, dict[str, str]]] = {
    "VG:CONCEPT:AGNIDH-FIRE-KINDLER": {
        "in_classical_sixteen": "true",
        "basis": (
            "The agnīdh is one of the sixteen rtvij of the Srautasutra schema, the "
            "Brahman-side priest who kindles and tends the fire. The null was a missing "
            "classification and not a ruling that the role stands outside the schema."
        ),
    },
    "VG:CONCEPT:POTR-PURIFIER": {
        "in_classical_sixteen": "true",
        "basis": (
            "The potṛ is one of the sixteen rtvij, among the Brahman's assistants. As "
            "above: the null was an unclassified row, not an exclusion."
        ),
    },
}

#: Sanskrit stem -> the registered :Devata the phenomenon is personified as, where one
#: exists. Written out rather than derived by a prefix match on the entity key, because a
#: prefix match paired USAS-DAWN with USASANAKTA -- the dual Dawn-and-Night -- which is a
#: different deity, and paired AGNI-FIRE with seven compounds.
PERSONIFICATION: Final[dict[str, str | None]] = {
    "VG:CONCEPT:AGNI-FIRE": "VG:DEVATA:AGNIH",
    "VG:CONCEPT:AP-WATERS": "VG:DEVATA:APAH",
    "VG:CONCEPT:RATRI-NIGHT": "VG:DEVATA:RATRIH",
    "VG:CONCEPT:SURYA-SUN": "VG:DEVATA:SURYAH",
    "VG:CONCEPT:USAS-DAWN": None,
    "VG:CONCEPT:AHAN-DAY": None,
    "VG:CONCEPT:CANDRAMAS-MOON": None,
    "VG:CONCEPT:JYOTIS-LIGHT": None,
    "VG:CONCEPT:SAMUDRA-OCEAN": None,
    "VG:CONCEPT:TAMAS-DARKNESS": None,
    "VG:CONCEPT:VATA-WIND": None,
    "VG:CONCEPT:VIDYUT-LIGHTNING": None,
    "VG:CONCEPT:VRSTI-RAIN": None,
}

#: Confirmed absent from the only ingested source, per agent7's per-key disposition.
TRANSLATION_SOURCE_ABSENT: Final[tuple[str, ...]] = (
    "VG:RV:SAK:M10:S086:V016",
    "VG:RV:SAK:M10:S086:V017",
)

#: The four whose anchor rendering is still typed MANTRA, with the anchor each shares.
TRANSLATION_RETYPE: Final[dict[str, str]] = {
    "VG:RV:SAK:M05:S055:V008": "VG:RV:SAK:M05:S055:V007",
    "VG:RV:SAK:M09:S007:V009": "VG:RV:SAK:M09:S007:V008",
    "VG:RV:SAK:M10:S048:V007": "VG:RV:SAK:M10:S048:V006",
    "VG:RV:SAK:M10:S132:V005": "VG:RV:SAK:M10:S132:V004",
}


def _scalar(session: Any, query: str, **params: Any) -> Any:
    record = session.run(Query(query, timeout=TIMEOUT), **params).single()
    return None if record is None else record[0]


def main() -> int:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            # -- RITUAL-004 ------------------------------------------------------
            roles = [
                dict(record)
                for record in session.run(
                    Query(
                        "MATCH (r:RitualRole) RETURN r.entity_key AS entity_key, "
                        "r.display_label AS label, r.in_classical_sixteen AS c16, "
                        "r.denominator_schema AS schema, "
                        "r.existence_evidence_type AS evidence "
                        "ORDER BY r.entity_key",
                        timeout=TIMEOUT,
                    )
                )
            ]
            hotr_edges = _scalar(
                session,
                "MATCH (:Ritual)-[r:PERFORMED_BY]->(:RitualRole {entity_key:$k}) "
                "RETURN count(r)",
                k="VG:CONCEPT:HOTR-PRIEST",
            )

            # -- ENTITY-007 -------------------------------------------------------
            phenomena = [
                dict(record)
                for record in session.run(
                    Query(
                        "MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS entity_key, "
                        "n.display_label AS label ORDER BY n.entity_key",
                        timeout=TIMEOUT,
                    )
                )
            ]
            live_devatas = {
                record["k"]
                for record in session.run(
                    Query("MATCH (d:Devata) RETURN d.entity_key AS k", timeout=TIMEOUT)
                )
            }

            # -- COMMUNITIES-002 ---------------------------------------------------
            declared = yaml.safe_load(
                (PROJECT_ROOT / "data" / "registry" / "devata_components.yaml").read_text(
                    encoding="utf-8"
                )
            )["components"]
            by_composite = {row["composite_entity_id"]: row for row in declared}
            landed = {
                record["k"]
                for record in session.run(
                    Query(
                        "MATCH (a:Devata)-[:COMPOSED_OF]->(:Devata) "
                        "RETURN DISTINCT a.entity_key AS k",
                        timeout=TIMEOUT,
                    )
                )
            }
            composites = [
                dict(record)
                for record in session.run(
                    Query(
                        "MATCH (d:Devata) WHERE d.structure IN ['PAIR','GROUP'] "
                        "RETURN d.entity_key AS entity_key, d.structure AS structure, "
                        "coalesce(d.component_count,0) AS component_count "
                        "ORDER BY d.entity_key",
                        timeout=TIMEOUT,
                    )
                )
            ]

            # -- TRANSLATION-004 ---------------------------------------------------
            untranslated = [
                record["k"]
                for record in session.run(
                    Query(
                        "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() "
                        "RETURN m.canonical_key AS k ORDER BY k",
                        timeout=TIMEOUT,
                    )
                )
            ]
            # The anchor of a covered verse is the nearest preceding verse in the same
            # hymn that DOES carry a rendering. Derived, not assumed: an anchor guessed as
            # "verse number minus one" breaks wherever two consecutive verses are covered.
            anchors: dict[str, dict[str, Any]] = {}
            for key in untranslated:
                if key in TRANSLATION_SOURCE_ABSENT:
                    continue
                row = session.run(
                    Query(
                        """
                        MATCH (m:Mantra {canonical_key: $key})
                        WITH m, left($key, size($key)-3) AS hymn_prefix,
                             toInteger(right($key, 3)) AS verse
                        MATCH (a:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
                        WHERE a.canonical_key STARTS WITH hymn_prefix
                          AND toInteger(right(a.canonical_key, 3)) < verse
                        RETURN a.canonical_key AS anchor, t.translation_id AS translation_id,
                               t.alignment_level AS alignment_level
                        ORDER BY toInteger(right(a.canonical_key, 3)) DESC
                        LIMIT 1
                        """,
                        timeout=TIMEOUT,
                    ),
                    key=key,
                ).single()
                if row is not None:
                    anchors[key] = dict(row)
    finally:
        driver.close()

    # ---------------- build the staged rows ----------------

    role_rows = []
    for role in roles:
        ruling = RITUAL_ROLE_RULINGS.get(role["entity_key"])
        role_rows.append(
            {
                "entity_key": role["entity_key"],
                "label": role["label"],
                "in_classical_sixteen_before": role["c16"],
                "in_classical_sixteen_after": (
                    True if ruling else role["c16"]
                ),
                "classified_by_r4": bool(ruling),
                "basis": ruling["basis"] if ruling else None,
                # One kind of value per field: the identifier here, the prose beside it.
                "denominator_schema_after": CLASSICAL_SCHEMA,
                "denominator_schema_note_after": (
                    "The sixteen officiants are a SRAUTASUTRA schema, not a Samhita one. "
                    "Any completeness figure over sixteen is a figure against that schema "
                    "and is labelled so, which is what GAP-RITUAL-004 requires."
                ),
                "schema_field_before": role["schema"],
            }
        )
    flagged_after = sum(1 for row in role_rows if row["in_classical_sixteen_after"] is True)

    phenomenon_rows = []
    for phenomenon in phenomena:
        key = phenomenon["entity_key"]
        devata = PERSONIFICATION.get(key, None)
        if key not in PERSONIFICATION:
            status, reason, target = (
                "UNATTEMPTED_NOT_IN_THE_R4_RULING_SET",
                "This phenomenon was not among the 13 ruled in R4. Unattempted, not refused.",
                None,
            )
        elif devata is not None and devata in live_devatas:
            status, reason, target = (
                "PERSONIFIED_AS_A_REGISTERED_DEVATA",
                "A :Devata carrying this phenomenon's own Sanskrit stem is registered, so "
                "the personification is a fact about this graph's registry and the deity "
                "key is recorded beside the status.",
                devata,
            )
        elif devata is not None:
            status, reason, target = (
                "REFUSED_NAMED_DEITY_NOT_IN_THE_REGISTRY",
                f"The expected counterpart {devata} is not a live :Devata.",
                None,
            )
        else:
            status, reason, target = (
                "REFUSED_NO_REGISTERED_DEITY_COUNTERPART",
                "No :Devata in this registry carries this phenomenon's Sanskrit stem. This "
                "is a statement about the registry, NOT about whether the Vedas personify "
                "the phenomenon -- several of these are addressed as beings in the text and "
                "were never curated as deities.",
                None,
            )
        phenomenon_rows.append(
            {
                "entity_key": key,
                "label": phenomenon["label"],
                "personification_status": status,
                "personification_status_reason": reason,
                "personified_as": target,
                "personification_contract": "VG:PERSONIFICATION_STATUS:V1",
            }
        )

    component_edges = []
    composite_rows = []
    unlanded = sorted(set(by_composite) - landed)
    for composite in composites:
        key = composite["entity_key"]
        if key in by_composite and key not in landed:
            declared_row = by_composite[key]
            members = [str(m) for m in declared_row["component_entity_ids"]]
            missing = [m for m in members if m not in live_devatas]
            if not members:
                # The registry declares the composite AND declines to enumerate it, with
                # its reasoning and a review status. That is a stronger refusal than "no
                # entry" and must not be lumped with it: viśvedevāḥ is REJECTED because
                # treating a collective as the set of all registered deities "would
                # fabricate thousands of edges the tradition does not assert", and
                # dyāvāpṛthivyau is NEEDS_REVIEW because half a decomposition is not one.
                composite_rows.append(
                    {
                        "entity_key": key,
                        "structure": composite["structure"],
                        "decomposition_status": "NOT_ENUMERABLE_DECLARED_BY_THE_REGISTRY",
                        "decomposition_status_reason": declared_row.get("evidence"),
                        "component_registry_review_status": declared_row.get("review_status"),
                        "component_registry_notes": declared_row.get("notes"),
                    }
                )
                continue
            if missing:
                composite_rows.append(
                    {
                        "entity_key": key,
                        "structure": composite["structure"],
                        "decomposition_status": "REFUSED_DECLARED_MEMBER_NOT_IN_THE_REGISTRY",
                        "decomposition_status_reason": (
                            f"devata_components.yaml declares members {missing} that are "
                            "not live :Devata nodes, so landing the decomposition would "
                            "create an edge to nothing."
                        ),
                    }
                )
                continue
            for member in members:
                component_edges.append(
                    {
                        "composite": key,
                        "component": member,
                        "properties": {
                            "component_policy_version": "rigveda-devata-component-policy-v1",
                            "knowledge_layer": "SOURCE_EXPLICIT",
                            "quality_tier": "TIER_A",
                            "evidence": declared_row.get("evidence"),
                            "r4_created_by": "scripts/r4_stage_combined.py",
                        },
                    }
                )
            composite_rows.append(
                {
                    "entity_key": key,
                    "structure": composite["structure"],
                    "component_count": len(members),
                    "decomposition_status": "DECOMPOSED_FROM_THE_COMPONENT_REGISTRY",
                    "decomposition_status_reason": (
                        "devata_components.yaml declares this composite's members with its "
                        "own evidence, and every member is a live :Devata."
                    ),
                }
            )
        elif key in landed:
            composite_rows.append(
                {
                    "entity_key": key,
                    "structure": composite["structure"],
                    "decomposition_status": "DECOMPOSED_FROM_THE_COMPONENT_REGISTRY",
                    "decomposition_status_reason": "Already landed before R4.",
                }
            )
        else:
            composite_rows.append(
                {
                    "entity_key": key,
                    "structure": composite["structure"],
                    "decomposition_status": "NOT_ENUMERABLE_FROM_ANYTHING_HELD",
                    "decomposition_status_reason": (
                        "No entry in data/registry/devata_components.yaml, which is the "
                        "only artifact in this repository that states a composite deity's "
                        "members. Enumerating this one means deciding which deities it "
                        "contains, which is curation rather than projection. For an "
                        "open-ended group -- devāḥ, viśve devāḥ, the waters -- membership "
                        "is a scholarly question and may have no enumerable answer; the "
                        "registry's own source_dependency says so."
                    ),
                }
            )

    translation_edges = []
    translation_retypes = []
    translation_rows = []
    for key in untranslated:
        if key in TRANSLATION_SOURCE_ABSENT:
            translation_rows.append(
                {
                    "canonical_key": key,
                    "translation_coverage": "SOURCE_ABSENT",
                    "translation_coverage_reason": (
                        "Absent from the only ingested source, confirmed by agent7's "
                        "per-key disposition. No edge is created."
                    ),
                }
            )
            continue
        anchor = anchors.get(key)
        if anchor is None:
            translation_rows.append(
                {
                    "canonical_key": key,
                    "translation_coverage": "UNRESOLVED_NO_ANCHOR_FOUND",
                    "translation_coverage_reason": (
                        "No preceding verse in the same hymn carries a rendering, so there "
                        "is no merged unit for this verse to be inside."
                    ),
                }
            )
            continue
        needs_retype = anchor["alignment_level"] != "MANTRA_RANGE"
        if needs_retype:
            translation_retypes.append(
                {
                    "translation_id": anchor["translation_id"],
                    "anchor": anchor["anchor"],
                    "covered": key,
                    "alignment_level_before": anchor["alignment_level"],
                    "alignment_level_after": "MANTRA_RANGE",
                    "basis": (
                        "The anchor's printed unit carries 4 lines where every other unit "
                        "in the hymn carries 2 or 3, so this verse's English is inside it. "
                        "Re-typing states the scope Griffith printed; splitting his prose "
                        "would fabricate."
                    ),
                }
            )
        translation_edges.append(
            {
                "mantra_key": key,
                "translation_id": anchor["translation_id"],
                "properties": {
                    "alignment_level": "MANTRA_RANGE",
                    "range_anchor": anchor["anchor"],
                    "knowledge_layer": "SOURCE_EXPLICIT",
                    "quality_tier": "TIER_B",
                    "evidence_basis": "SOURCE_METADATA",
                    "attribution_precision": "CONTAINER_INHERITED",
                    "language": "en",
                    "translator": "Griffith",
                    "coverage_note": (
                        "The source merged this verse with its anchor into one printed "
                        "unit, so this edge reaches the anchor's rendering rather than a "
                        "rendering of its own. No text was split or created."
                    ),
                    "r4_created_by": "scripts/r4_stage_combined.py",
                },
            }
        )
        translation_rows.append(
            {
                "canonical_key": key,
                "translation_coverage": "COVERED_BY_A_MERGED_RANGE_ON_ITS_ANCHOR",
                "range_anchor": anchor["anchor"],
                "translation_coverage_reason": (
                    "Griffith prints this verse inside its anchor's unit. The edge points "
                    "at the anchor's existing Translation node."
                ),
            }
        )

    report = {
        "artifact": "R4_COMBINED_STAGING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "GAP-RITUAL-004": {
            "roles": len(role_rows),
            "in_classical_sixteen_before": sum(1 for r in role_rows if r["in_classical_sixteen_before"] is True),
            "in_classical_sixteen_after": flagged_after,
            "unclassified_before": sum(1 for r in role_rows if r["in_classical_sixteen_before"] is None),
            "unclassified_after": sum(1 for r in role_rows if r["in_classical_sixteen_after"] is None),
            "hotr_performed_by_edges": hotr_edges,
            "schema_field_kinds_before": dict(
                collections.Counter(
                    "IDENTIFIER" if r["schema_field_before"] == CLASSICAL_SCHEMA
                    else "PROSE" if r["schema_field_before"] else "NULL"
                    for r in role_rows
                )
            ),
            "rows": role_rows,
        },
        "GAP-ENTITY_COVERAGE-007": {
            "phenomena": len(phenomenon_rows),
            "with_a_status_before": 0,
            "with_a_status_after": len(phenomenon_rows),
            "status_distribution": dict(
                collections.Counter(r["personification_status"] for r in phenomenon_rows)
            ),
            "rows": phenomenon_rows,
        },
        "GAP-COMMUNITIES-002": {
            "composites": len(composite_rows),
            "registry_declares": len(by_composite),
            "already_landed": len(landed),
            "unlanded_in_the_registry": unlanded,
            "r3_claimed_mechanical_pairs": 24,
            "actually_supported_by_the_registry": len(unlanded),
            "r3_figure_correction": (
                "R3 recorded 24 PAIRs as mechanical decomposition over "
                "devata_components.yaml. The file declares 20 composites, 14 are landed, "
                f"and {len(unlanded)} remain -- so {len(unlanded)} are mechanical and the "
                "other 51 need curation the repository does not hold."
            ),
            "component_edges_staged": len(component_edges),
            "status_distribution": dict(
                collections.Counter(r["decomposition_status"] for r in composite_rows)
            ),
            "rows": composite_rows,
            "component_edges": component_edges,
        },
        "GAP-TRANSLATION-004": {
            "untranslated_before": len(untranslated),
            "source_absent": list(TRANSLATION_SOURCE_ABSENT),
            "covered_by_a_merged_range": len(translation_edges),
            "anchors_needing_a_retype": len(translation_retypes),
            "unresolved": [
                r["canonical_key"]
                for r in translation_rows
                if r["translation_coverage"] == "UNRESOLVED_NO_ANCHOR_FOUND"
            ],
            "untranslated_after": len(TRANSLATION_SOURCE_ABSENT)
            + sum(
                1
                for r in translation_rows
                if r["translation_coverage"] == "UNRESOLVED_NO_ANCHOR_FOUND"
            ),
            "retypes": translation_retypes,
            "edges": translation_edges,
            "rows": translation_rows,
        },
        "promised": {
            "ritual_role_nodes_updated": len(role_rows),
            "phenomenon_nodes_updated": len(phenomenon_rows),
            "composite_nodes_updated": len(composite_rows),
            "composed_of_edges_created": len(component_edges),
            "translation_nodes_retyped": len(translation_retypes),
            "has_translation_edges_created": len(translation_edges),
            "mantra_nodes_updated": len(translation_rows),
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "staging.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  R4 COMBINED STAGING")
    print()
    r4 = report["GAP-RITUAL-004"]
    print(f"  RITUAL-004      roles {r4['roles']}  classical-sixteen "
          f"{r4['in_classical_sixteen_before']} -> {r4['in_classical_sixteen_after']}  "
          f"unclassified {r4['unclassified_before']} -> {r4['unclassified_after']}  "
          f"hotr PERFORMED_BY {r4['hotr_performed_by_edges']}")
    e7 = report["GAP-ENTITY_COVERAGE-007"]
    print(f"  ENTITY-007      phenomena {e7['phenomena']}  status 0 -> "
          f"{e7['with_a_status_after']}  {e7['status_distribution']}")
    c2 = report["GAP-COMMUNITIES-002"]
    print(f"  COMMUNITIES-002 composites {c2['composites']}  registry declares "
          f"{c2['registry_declares']}  landed {c2['already_landed']}  "
          f"unlanded {len(c2['unlanded_in_the_registry'])}  edges {c2['component_edges_staged']}")
    print(f"                  {c2['status_distribution']}")
    t4 = report["GAP-TRANSLATION-004"]
    print(f"  TRANSLATION-004 untranslated {t4['untranslated_before']} -> "
          f"{t4['untranslated_after']}  range edges {t4['covered_by_a_merged_range']}  "
          f"retypes {t4['anchors_needing_a_retype']}  unresolved {t4['unresolved']}")
    print()
    print(f"  staged: {(OUT / 'staging.json').relative_to(PROJECT_ROOT)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
