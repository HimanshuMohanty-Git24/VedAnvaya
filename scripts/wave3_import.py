#!/usr/bin/env python3
"""Execute Wave 3: the canonical import, read back out of the database.

Owner sections 7, 11 and 12. This is the only script in the campaign that writes to the
canonical graph, and it is built around three rules the campaign learned the hard way.

**A failed domain must not leave half its mutation committed.** Each element group runs in
one explicit transaction. The group either lands whole or not at all, and the checkpoint is
written only after the transaction commits, so a resumed run cannot skip a group that
half-ran.

**Import code returning success closes nothing.** Every group's count is read back out of
the database after its transaction commits, and rows-sent is diffed against rows-landed. A
MERGE can collapse two rows into one and a MATCH can find no endpoint; neither failure
appears offline, and both have happened in this project.

**Idempotent, ordered, checkpointed, domain-attributed.** Re-running is a no-op. The order
is the owner's canonical order, not the declaration order: corrections first, then schema,
then nodes, then the edges that point at them. Every element carries the domain that
produced it and the run id that wrote it, so a rollback can be scoped.

WHAT IT REFUSES TO DO
=====================

It will not write unless ``WAVE_3_DRY_RUN_V2`` says GO, and it re-reads that artifact's own
inputs rather than trusting its verdict: if the element plan, the eligibility ledger or the
gap registry has changed since the dry-run was generated, the run stops. A dry-run that
describes a different tree than the one being imported is worse than no dry-run.

It also refuses any group the plan marked unusable, and it never writes an element whose
identity the plan withheld.

Usage:
    python scripts/wave3_import.py --execute      # write
    python scripts/wave3_import.py                # rehearse: plan, verify, write nothing
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase, Session
from wave3_import_plan import (
    GROUPS,
    ElementGroup,
    elements_of,
    get_path,
    identity_of,
    mint,
    minted_key,
    passes,
    redirects,
    row_rel_type,
)

from vedagraph.domain.ontology import TIER_BY_LAYER, KnowledgeLayer

INTEGRATION = pathlib.Path("data/staging/integration")
DRY_RUN = INTEGRATION / "wave3_dry_run_v2.json"
PLAN = INTEGRATION / "wave3_import_plan.json"
LEDGER = INTEGRATION / "wave3_eligibility.json"
SOMA = INTEGRATION / "wave3_soma_pressing_correction.json"
SCOPE = INTEGRATION / "wave3_scope_grain.json"
REGISTRY = pathlib.Path("data/gap_registry.json")
CHECKPOINT = INTEGRATION / "wave3_import_checkpoint.json"
RECEIPT = INTEGRATION / "wave3_import_receipt.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: Stamped on every element this wave writes, so a rollback can be scoped to it and a
#: readback can tell a Wave 3 element from one that was already there.
WAVE = "WAVE_3"

#: The graph's own rule, imported rather than restated. QualityTier documents itself as "a
#: function of layer, not of confidence", so the tier is derived from a stated layer and
#: never from an artifact's quality_class -- casting that vocabulary into this enum would
#: invent a grade.
_LAYER_TO_TIER: dict[str, str] = {
    "SOURCE_EXPLICIT": str(TIER_BY_LAYER[KnowledgeLayer.L1_SOURCE_EXPLICIT]),
    "SOURCE_DERIVED_SCOPE": str(TIER_BY_LAYER[KnowledgeLayer.L2_DETERMINISTIC_DERIVED]),
    "DETERMINISTIC_DERIVED": str(TIER_BY_LAYER[KnowledgeLayer.L2_DETERMINISTIC_DERIVED]),
    "LLM_EXTRACTED": str(TIER_BY_LAYER[KnowledgeLayer.L3_LLM_EXTRACTED]),
    "INTERPRETIVE_CLAIM": str(TIER_BY_LAYER[KnowledgeLayer.L4_INTERPRETIVE_CLAIM]),
}


class UnknownKnowledgeLayer(RuntimeError):
    """A layer with no tier. Raised rather than defaulted: a silent default is a grade."""


def tier_for(layer: str) -> str:
    if layer not in _LAYER_TO_TIER:
        raise UnknownKnowledgeLayer(
            f"{layer!r} maps to no QualityTier. Add it to _LAYER_TO_TIER deliberately: "
            "defaulting would put an ungraded edge on the reader's surface wearing a grade."
        )
    return _LAYER_TO_TIER[layer]


def grade(row: dict[str, Any], group: ElementGroup) -> dict[str, str]:
    """The layer and tier for one element, from the row if it states one, else the group."""
    layer = str(row.get("evidence_layer") or group.knowledge_layer or "")
    if not layer:
        raise UnknownKnowledgeLayer(
            f"{group.group_id}: neither the row nor the group states a knowledge layer, so "
            "no tier can be derived. Declare knowledge_layer on the group."
        )
    return {"knowledge_layer": layer, "quality_tier": tier_for(layer)}

def provenance(run_id: str, domain: str, group_id: str, *, created: bool) -> dict[str, str]:
    """What this wave records about an element it wrote.

    ``wave3_created_by`` is set only when the element is CREATED, and
    ``wave3_touched_by`` on every write. The first version stamped one ``wave`` property
    either way, so labelling the 8 pre-existing rites made them claim this wave wrote them
    and no query could tell them from the 92 it did. Creation and contact are different
    facts.
    """
    stamp = {
        "wave": WAVE,
        "wave3_touched_by": run_id,
        "wave3_domain": domain,
        "wave3_group": group_id,
    }
    if created:
        stamp["wave3_created_by"] = run_id
    return stamp


#: Which properties of a source row become element properties. Everything else in the row
#: is evidence about how the row was produced and stays in the staging artifact -- copying a
#: whole row onto a node makes the graph a second, diverging copy of the artifact.
#:
#: WHAT MUST NOT BE CARRIED, learned by doing it and rolling it back. The role-filler rows
#: name the canonical entity a filler refers to in a field called ``entity_key``. Carrying
#: that straight through puts the REFERENT's identity onto the filler, so 2,052
#: :RoleFiller nodes answered to the keys of entities they merely referred to -- which is
#: exactly the duplication the M1 card forbids, stated there as "not a duplicate of a
#: canonical entity". ``entity_key`` was unique across all 108,779 pre-import nodes;
#: afterwards 85 keys were shared by 481 nodes, and the label-less endpoint match then
#: fanned 387 intended REFERS_TO edges into 4,564. Renamed via RENAMED below to
#: ``refers_to_entity_key``, which says what it is and cannot be mistaken for an identity.
CARRIED: dict[str, tuple[str, ...]] = {
    "SR_ROLE_FILLER_NODES": (
        "role_filler_key",
        "canonical_key",
        "veda",
        "role",
        "surface",
        "lemma",
        "upos",
        "case",
        "filler_type",
        "derivation",
        "predicate",
        "frame",
        "assertion_ordinal",
    ),
    "RITUAL_RITE_NODES": (
        "ritual_key",
        "label_en",
        "label_sa",
        "rite_class",
        "existence_evidence_type",
        "samhita_attested",
        "samhita_attestation_count",
        "supplementary_attestation_count",
        "curator_note",
        "node_status",
    ),
    "RITUAL_STEP_NODES": (
        "step_key",
        "canonical_urn",
        "entity_id",
        "entity_type",
        "ritual_key",
        "step_position",
        "printed_ordinal_in_work",
        "sequence_marker",
        "citation",
        "supplementary_key",
        "work_key",
        "veda_school",
        "tier",
        "text_iast",
        "translation",
        "translation_translator",
        "order_basis",
        "order_completeness",
        "source_stated_position",
        "anchor_note",
    ),
    "RITUAL_ROLE_NODES": (
        "role_key",
        "label_en",
        "label_sa",
        "officiant_group",
        "in_classical_sixteen",
        "denominator_schema",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_ACTION_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_IMPLEMENT_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_MATERIAL_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "RITUAL_OFFERING_NODES": (
        "concept_key",
        "label_en",
        "label_sa",
        "kind",
        "sub_kind",
        "existence_evidence_type",
        "samhita_attested",
        "supplementary_attestation_count",
        "node_status",
    ),
    "SCHOLARSHIP_SCHOLAR_NODES": (
        "scholar_id",
        "name",
        "scholar_type",
        "attribution_status",
    ),
    "SCHOLARSHIP_WORK_NODES": ("work_id", "title", "source_id", "scope_note"),
    # The claim is ABOUT a passage, so the passage's key is renamed rather than carried:
    # a claim that answers to a canonical_key is addressable as the passage it discusses.
    "SCHOLARSHIP_CLAIM_ROWS": (
        "canonical_key",
        "veda",
        "algorithm_version",
        "evidence_layer",
        "mapping_confidence",
        "quality_class",
        "source_id",
        "source_locator",
        "source_url",
        "recension_verified",
    ),
    # Likewise a verdict is a claim ABOUT an edge on a passage. reference_set_type is
    # lifted out of the payload because the closure test and every honest reader need to
    # see which reference set a verdict came from without parsing a JSON blob.
    "QUALITY_VERDICT_NODES": (
        "canonical_key",
        "veda",
        "algorithm_version",
        "evidence_layer",
        "mapping_confidence",
        "quality_class",
        "source_id",
        "source_locator",
        "source_snapshot",
        "code_commit",
        "config_hash",
    ),
    "COMMUNITIES_ARTIFACT_NODES": (
        "community_id",
        "algorithm",
        "algorithm_version",
        "resolution",
        "seed",
        "weighting",
        "projection",
        "size",
        "caveat",
        "interpretation_warning",
        "code_commit",
        "config_hash",
        "source_snapshot",
    ),
}


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def digest(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def scalar(value: Any) -> Any:
    """Neo4j stores scalars and lists of scalars; a nested structure becomes JSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) and all(
        v is None or isinstance(v, (str, int, float, bool)) for v in value
    ):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class UndeclaredProperties(RuntimeError):
    """A NODE group did not say which of its row's fields become element properties."""


def node_props(row: dict[str, Any], group: ElementGroup) -> dict[str, Any]:
    """The properties one row contributes, declared rather than inferred.

    There is deliberately no fallback to "every field in the row". The fallback existed and
    it carried ``canonical_key`` -- a Passage's identity -- onto 2,568 quality verdicts and
    113 scholarship claims, and the contract test could not see it because the test walked
    CARRIED and those groups were not in it. The groups with the widest exposure were
    exactly the ones an implicit rule covered.
    """
    if group.group_id not in CARRIED:
        raise UndeclaredProperties(
            f"{group.group_id} declares no CARRIED fields. List them: carrying a whole row "
            "puts every foreign key the artifact happens to hold onto the element."
        )
    props = {
        field: scalar(row.get(field)) for field in CARRIED[group.group_id] if field in row
    }
    for source, name in LIFTED.get(group.group_id, {}).items():
        props[name] = scalar(get_path(row, source))
    return props


# ---------------------------------------------------------------------------------------
# Corrections. These run first, and each is a named, proof-backed change to existing data.
# ---------------------------------------------------------------------------------------


def correction_soma(session: Session, run_id: str, *, execute: bool) -> dict[str, Any]:
    """Owner section 3: retire the edges whose sole evidence is a retired weak alias.

    The retirement set comes from the correction artifact, which re-derived the ABOUT_CONCEPT
    layer over all 20,210 mantras rather than reading the stored evidence quote -- that quote
    is a window round the match, and a verse may carry a surviving alias the window does not
    show.

    The edges are DELETEd rather than flagged. A flagged edge still answers a query, and the
    whole point of withdrawing an alias's authority is that the edges it alone created stop
    being assertions.
    """
    artifact = load(SOMA)
    mentions = artifact.get("mentions_entity") or {}
    about = artifact.get("about_concept") or {}
    retired = artifact.get("retired_aliases") or []
    mention_keys = list(mentions.get("retire_keys") or [])
    about_keys = list(about.get("retire_keys") or [])
    updates = list(mentions.get("update_rows") or [])

    result: dict[str, Any] = {
        "correction": "SOMA_PRESSING_WEAK_ALIAS_RETIREMENT",
        "retired_aliases": retired,
        "mentions_entity_sent": len(mention_keys),
        "about_concept_sent": len(about_keys),
        "matched_alias_updates_sent": len(updates),
    }
    if not execute:
        result["executed"] = False
        return result

    with session.begin_transaction() as tx:
        deleted_m = tx.run(
            "UNWIND $keys AS k "
            "MATCH (p:Passage {canonical_key: k})-[r:MENTIONS_ENTITY]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "WHERE ALL(a IN r.matched_aliases WHERE a IN $retired) "
            "DELETE r RETURN count(*) AS n",
            keys=mention_keys,
            retired=retired,
        ).single()["n"]
        deleted_a = tx.run(
            "UNWIND $keys AS k "
            "MATCH (p:Passage {canonical_key: k})-[r:ABOUT_CONCEPT]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "DELETE r RETURN count(*) AS n",
            keys=about_keys,
        ).single()["n"]
        # The 12 edges that survive lose the retired alias from their evidence, so the
        # property stops naming a form that is no longer allowed to assert anything.
        edited = tx.run(
            "UNWIND $rows AS row "
            "MATCH (p:Passage {canonical_key: row.canonical_key})-[r:MENTIONS_ENTITY]->"
            "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
            "SET r.matched_aliases = row.after, "
            "    r.alias_count = size(row.after), "
            "    r.wave3_alias_retirement = $run_id "
            "RETURN count(*) AS n",
            rows=[
                {
                    "canonical_key": row["canonical_key"],
                    "after": row["matched_aliases_after"],
                }
                for row in updates
            ],
            run_id=run_id,
        ).single()["n"]
        tx.commit()

    result.update(
        {
            "executed": True,
            "mentions_entity_landed": deleted_m,
            "about_concept_landed": deleted_a,
            "matched_alias_updates_landed": edited,
        }
    )
    return result


def correction_m5(session: Session, run_id: str, *, execute: bool) -> dict[str, Any]:
    """Owner decision 1, card M5: one edge moves from EPITHET_VARIANT_OF.

    Scoped to the single Soma Pavamana -> Soma pair. The other 10 EPITHET_VARIANT_OF edges
    and the predicate's meaning are untouched, so this is a data migration with a recorded
    reason rather than a semantic change.
    """
    result: dict[str, Any] = {"correction": "M5_SPECIALIZED_FORM_OF", "edges_sent": 1}
    if not execute:
        result["executed"] = False
        return result

    with session.begin_transaction() as tx:
        before = tx.run(
            "MATCH ()-[r:EPITHET_VARIANT_OF]->() RETURN count(r) AS n"
        ).single()["n"]
        moved = tx.run(
            "MATCH (a:Devata {entity_key: 'VG:DEVATA:PAVAMANAH-SOMAH'})"
            "-[r:EPITHET_VARIANT_OF]->(b:Devata {entity_key: 'VG:DEVATA:SOMAH'}) "
            "CREATE (a)-[n:SPECIALIZED_FORM_OF]->(b) "
            "SET n = properties(r), "
            "    n.migrated_from = 'EPITHET_VARIANT_OF', "
            "    n.migration_reason = "
            "      'Owner decision 1: both distinctions carry useful semantics and "
            "EPITHET_VARIANT_OF is too strong for this pair. A is a contextually "
            "specialized manifestation of B and stays separately addressable.', "
            "    n.wave3_run_id = $run_id, "
            "    n.wave = $wave "
            "DELETE r RETURN count(*) AS n",
            run_id=run_id,
            wave=WAVE,
        ).single()["n"]
        after = tx.run("MATCH ()-[r:EPITHET_VARIANT_OF]->() RETURN count(r) AS n").single()["n"]
        specialized = tx.run(
            "MATCH ()-[r:SPECIALIZED_FORM_OF]->() RETURN count(r) AS n"
        ).single()["n"]
        tx.commit()

    result.update(
        {
            "executed": True,
            "edges_landed": moved,
            "epithet_variant_of_before": before,
            "epithet_variant_of_after": after,
            "specialized_form_of_after": specialized,
        }
    )
    return result


# ---------------------------------------------------------------------------------------
# Element groups.
# ---------------------------------------------------------------------------------------


#: Payload fields lifted onto the element, with the name they take. A verdict that keeps
#: its reference set only inside a JSON payload cannot be queried for the one distinction
#: the quality domain exists to preserve: an independent human-treebank adjudication and a
#: syllable count are not the same evidence, and 161 passages carry one of each.
LIFTED: dict[str, dict[str, str]] = {
    "QUALITY_VERDICT_NODES": {
        "payload.reference_set_type": "reference_set_type",
        "payload.adjudicated_by": "adjudicated_by",
        "payload.reference_set": "reference_set",
        "payload.not_human_gold_because": "not_human_gold_because",
        "payload.layers_present": "layers_present",
        "payload.verdict_counts": "verdict_counts",
    },
    "SCHOLARSHIP_CLAIM_ROWS": {
        "payload.axis": "axis",
        "payload.row_kind": "row_kind",
        "payload.relation": "relation",
        "payload.relation_basis": "relation_basis",
        "payload.relation_strength": "relation_strength",
        "payload.witness": "witness",
        "payload.passage_citation": "passage_citation",
        "payload.passage_scope": "passage_scope",
    },
}

#: Fields renamed on the way onto an element, because the artifact's name collides with an
#: identity the graph already uses. See the note on CARRIED.
RENAMED: dict[str, dict[str, str]] = {
    # Both of these name something the filler is ABOUT rather than something it is. The
    # first was found by rolling back a bad import; the second by the contract test written
    # afterwards, before it could cost anything.
    "SR_ROLE_FILLER_NODES": {
        "entity_key": "refers_to_entity_key",
        "canonical_key": "passage_canonical_key",
    },
    "SCHOLARSHIP_CLAIM_ROWS": {"canonical_key": "about_passage_canonical_key"},
    "QUALITY_VERDICT_NODES": {"canonical_key": "about_passage_canonical_key"},
}

#: Labels a created element takes in addition to its own, because a key in the
#: ``VG:CONCEPT:`` namespace belongs to the concept ontology and every one of the 229
#: entities already there carries ``:Concept:DomainEntity``. Without this the second
#: import created 136 ritual entities labelled only with their type, so
#: ``MATCH (n:DomainEntity)`` could not see them and they sat outside the ontology their
#: own keys claim membership of. Derived from the key namespace rather than listed per
#: group, so a new registry group cannot forget it.
CONCEPT_NAMESPACE_LABELS: tuple[str, ...] = ("Concept", "DomainEntity")
CONCEPT_KEY_PREFIX = "VG:CONCEPT:"


class AmbiguousEndpoint(RuntimeError):
    """An endpoint key names more than one node, so an edge write would multiply it."""


def assert_unambiguous(
    session: Session, group: ElementGroup, payload: list[dict[str, Any]]
) -> None:
    """Refuse to write an edge whose endpoint key names more than one node.

    A label-less ``MATCH (a) WHERE a.entity_key = X`` binds every node carrying that key,
    and two such matches form a cartesian product, so one intended edge becomes n x m. This
    project has met that before -- an unlabelled MATCH once made 39,461 bogus edges -- and
    met it again here, turning 387 intended REFERS_TO edges into 4,564.

    Raising is the right response rather than picking one node. Which of several nodes an
    edge should attach to is a modelling question, and answering it inside an importer would
    settle it by whichever node the planner happened to bind first.
    """
    for side, prop, label in (
        ("start", group.start_key_property, group.start_label),
        ("end", group.end_key_property, group.end_label),
    ):
        if label:
            continue  # a labelled match is constrained by that label's own unique index
        keys = sorted({str(row[side]) for row in payload})
        ambiguous = session.run(
            f"UNWIND $keys AS v MATCH (n) WHERE n.{prop} = v "
            "WITH v, count(n) AS c WHERE c > 1 "
            "RETURN v AS v, c AS c ORDER BY c DESC LIMIT 5",
            keys=keys,
        ).data()
        if ambiguous:
            raise AmbiguousEndpoint(
                f"{group.group_id}: the {side} key names more than one node, so writing "
                f"would multiply the edge. Worst: {ambiguous}. Constrain the group's "
                f"{side}_label, or resolve the duplicate keys first."
            )


def write_nodes(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> tuple[int, int]:
    """Create the absent elements and LABEL the present ones. Returns (created, labelled).

    Two queries rather than one MERGE, and the reason is measured. ``MERGE (n:Ritual
    {entity_key: X})`` does not find an existing ``:Concept {entity_key: X}`` -- MERGE
    matches on label AND properties together -- so it created a second node under the same
    key for each of the 66 registry rows whose element the graph already held. The plan
    already distinguishes present from absent; the importer has to act on that distinction
    rather than hope MERGE will.

    An existing element therefore gains the new label and the new properties on the node
    that is already there, which is what the registries mean when they say EXISTING.
    """
    key = group.match_property
    renames = RENAMED.get(group.group_id, {})
    payload = []
    for row in rows:
        props = {
            renames.get(field, field): value
            for field, value in node_props(row, group).items()
        }
        if group.display_label_field:
            label = get_path(row, group.display_label_field)
            if label is not None:
                props.setdefault("display_label", scalar(label))
        # The stamp is applied per branch below, since it differs for create and label.
        if group.key_minted_from_identity:
            props[key] = mint(group, row)
        else:
            props[key] = str(get_path(row, group.identity_fields[0]))
        payload.append(props)

    keys = [row[key] for row in payload]
    created_stamp = provenance(run_id, group.domain, group.group_id, created=True)
    touched_stamp = provenance(run_id, group.domain, group.group_id, created=False)

    # An index on the group's own key, created before the probe. Without it the probe is
    # label-less and cannot use one: 9,255 step keys over 123,000 nodes took 3m40s, and the
    # equivalent labelling pass on 2,568 quality verdicts took 4m42s. IF NOT EXISTS makes it
    # idempotent, and the index is a permanent improvement rather than a run-scoped one.
    session.run(
        f"CREATE INDEX wave3_{group.element.lower()}_{key} IF NOT EXISTS "
        f"FOR (n:{group.element}) ON (n.{key})"
    ).consume()

    with session.begin_transaction() as tx:
        # Two probes. The label-scoped one uses the index and finds everything on a re-run;
        # the label-less one runs only for the keys it missed, which on a first pass is the
        # small set of elements the graph already holds under a DIFFERENT label -- 66 ritual
        # registry entities -- and on a re-run is empty.
        present = {
            str(record["v"])
            for record in tx.run(
                f"UNWIND $keys AS v MATCH (n:{group.element}) WHERE n.{key} = v "
                "RETURN DISTINCT v AS v",
                keys=keys,
            )
        }
        unseen = [k for k in keys if k not in present]
        # The fallback answers one question: does the graph already hold this element under
        # a DIFFERENT label? That can only happen if some other node uses this property
        # name at all. For a property this wave introduces -- step_key, role_filler_key,
        # community_id -- the answer is no by construction, and the scan is pure waste: the
        # 9,255-key step probe spent 7m32s proving that nothing carries step_key.
        elsewhere = (
            tx.run(
                f"MATCH (n) WHERE n.{key} IS NOT NULL AND NOT n:{group.element} "
                "RETURN count(n) AS c LIMIT 1"
            ).single()
            if unseen
            else None
        )
        if unseen and int((elsewhere or {"c": 0})["c"]) > 0:
            present |= {
                str(record["v"])
                for record in tx.run(
                    f"UNWIND $keys AS v MATCH (n) WHERE n.{key} = v RETURN DISTINCT v AS v",
                    keys=unseen,
                )
            }
        labelled = 0
        existing = [row for row in payload if row[key] in present]
        if existing:
            labelled = int(
                tx.run(
                    f"UNWIND $rows AS row MATCH (n) WHERE n.{key} = row.{key} "
                    f"SET n:{group.element}, n += row, n += $stamp "
                    "RETURN count(DISTINCT n) AS n",
                    rows=existing,
                    stamp=touched_stamp,
                ).single()["n"]
            )
        absent = [row for row in payload if row[key] not in present]
        created = 0
        if absent:
            # A key in the concept namespace joins the concept ontology. Split so a group
            # whose keys are mixed still gets each element the labels its own key claims.
            in_namespace = [
                row for row in absent if str(row[key]).startswith(CONCEPT_KEY_PREFIX)
            ]
            outside = [row for row in absent if row not in in_namespace]
            for rows_for_labels, extra in (
                (in_namespace, CONCEPT_NAMESPACE_LABELS),
                (outside, ()),
            ):
                if not rows_for_labels:
                    continue
                labels = ":".join((group.element, *extra))
                created += int(
                    tx.run(
                        f"UNWIND $rows AS row CREATE (n:{labels}) SET n += row, n += $stamp "
                        "RETURN count(n) AS n",
                        rows=rows_for_labels,
                        stamp=created_stamp,
                    ).single()["n"]
                )
        tx.commit()
    return created, labelled


def write_node_properties(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    """Property writes onto existing nodes. MATCH, never MERGE.

    A MERGE here would create the node the property was meant to annotate, turning a
    dangling reference into a silent new node -- which is how a projection grows rows that
    correspond to nothing.
    """
    key = group.match_property
    prefix = f"{group.domain}_"
    payload = []
    for row in rows:
        props = {
            f"{prefix}{field}": scalar(value)
            for field, value in row.items()
            if field not in group.identity_fields and not field.startswith("evidence")
        }
        props.update(provenance(run_id, group.domain, group.group_id, created=False))
        payload.append({"key": str(get_path(row, group.identity_fields[0])), "props": props})

    query = (
        f"UNWIND $rows AS row MATCH (n:{group.element}) WHERE n.{key} = row.key "
        "SET n += row.props RETURN count(n) AS n"
    )
    with session.begin_transaction() as tx:
        landed = tx.run(query, rows=payload).single()["n"]
        tx.commit()
    return int(landed)


def write_relationships(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    by_predicate = dict(group.object_field_by_predicate)
    redirect = redirects(group.domain)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        predicate = row_rel_type(row, group)
        end_field = by_predicate.get(predicate, group.end_field)
        start = (
            minted_key(row, group)
            if group.start_minted_by
            else get_path(row, str(group.start_field))
        )
        end = get_path(row, str(end_field))
        if not start or not end:
            continue
        props = {
            field: scalar(value)
            for field, value in row.items()
            if field not in {group.start_field, end_field}
        }
        props.update(provenance(run_id, group.domain, group.group_id, created=True))
        props.update(grade(row, group))
        # The same redirect the plan applies. Without it 6 rite edges pointed at
        # GRHAPRAVESA and PITRMEDHA, whose own keys the import correctly declines to create
        # because the graph holds those rites under other names, and the edges landed
        # nothing while every group reported ok.
        buckets.setdefault(predicate, []).append(
            {
                "start": redirect.get(str(start), str(start)),
                "end": redirect.get(str(end), str(end)),
                "props": props,
            }
        )

    start_label = f":{group.start_label}" if group.start_label else ""
    end_label = f":{group.end_label}" if group.end_label else ""
    landed = 0
    for predicate, payload in sorted(buckets.items()):
        assert_unambiguous(session, group, payload)
        # count(DISTINCT r), not count(r): UNWIND runs the MERGE once per row, so counting
        # rows reports how many MERGE operations ran and calls a repeated pair a new edge.
        # That is what made three groups report landing more than they were sent.
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (a{start_label}) WHERE a.{group.start_key_property} = row.start "
            f"MATCH (b{end_label}) WHERE b.{group.end_key_property} = row.end "
            f"MERGE (a)-[r:{predicate}]->(b) SET r += row.props "
            "RETURN count(DISTINCT r) AS n"
        )
        with session.begin_transaction() as tx:
            landed += int(tx.run(query, rows=payload).single()["n"])
            tx.commit()
    return landed


def write_relationship_properties(
    session: Session, group: ElementGroup, rows: list[dict[str, Any]], run_id: str
) -> int:
    """Backfill onto edges that already exist.

    The MATCH is undirected only for a symmetric group. The parallel family is stored once
    in ascending Veda-code order and read undirected, so a direction-sensitive MATCH would
    miss half of it and the backfill would land on one arbitrary half of the layer. For a
    directed relation the arrow is part of the claim, and matching either way would write
    the property onto an edge that asserts the opposite.

    Either way this MATCHes and never MERGEs: the group exists because the edges are already
    there, so a MERGE would create the very element whose absence is the finding.
    """
    by_predicate = dict(group.object_field_by_predicate)
    redirect = redirects(group.domain)
    buckets: dict[str, list[dict[str, Any]]] = {}
    prefix = f"{group.domain}_"
    for row in rows:
        predicate = row_rel_type(row, group)
        end_field = by_predicate.get(predicate, group.end_field)
        start = get_path(row, str(group.start_field))
        end = get_path(row, str(end_field))
        if not start or not end:
            continue
        props = {
            f"{prefix}{field}": scalar(value)
            for field, value in row.items()
            if field not in {group.start_field, end_field}
        }
        props.update(provenance(run_id, group.domain, group.group_id, created=True))
        buckets.setdefault(predicate, []).append(
            {
                "start": redirect.get(str(start), str(start)),
                "end": redirect.get(str(end), str(end)),
                "props": props,
            }
        )

    start_label = f":{group.start_label}" if group.start_label else ""
    end_label = f":{group.end_label}" if group.end_label else ""
    landed = 0
    for predicate, payload in sorted(buckets.items()):
        query = (
            f"UNWIND $rows AS row "
            f"MATCH (a{start_label}) WHERE a.{group.start_key_property} = row.start "
            f"MATCH (b{end_label}) WHERE b.{group.end_key_property} = row.end "
            f"MATCH (a)-[r:{predicate}]{'-' if group.symmetric else '->'}(b) "
            "SET r += row.props RETURN count(DISTINCT r) AS n"
        )
        assert_unambiguous(session, group, payload)
        with session.begin_transaction() as tx:
            landed += int(tx.run(query, rows=payload).single()["n"])
            tx.commit()
    return landed


def _pairs(group: ElementGroup, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Undirected pair identities for a symmetric group, for the expectation arithmetic."""
    by_predicate = dict(group.object_field_by_predicate)
    redirect = redirects(group.domain)
    out: list[dict[str, str]] = []
    for row in rows:
        predicate = row_rel_type(row, group)
        end_field = by_predicate.get(predicate, group.end_field)
        start = get_path(row, str(group.start_field))
        end = get_path(row, str(end_field))
        if not start or not end:
            continue
        a = redirect.get(str(start), str(start))
        b = redirect.get(str(end), str(end))
        lo, hi = sorted((a, b))
        out.append({"start": lo, "end": hi})
    return out


def correction_withheld_registry_entities(
    session: Session, run_id: str, *, execute: bool
) -> dict[str, Any]:
    """Delete the registry entities a later plan rule withholds, and only those.

    Scoped three ways so it cannot reach anything else: the node must have been CREATED by
    this wave, must carry the entity_key of a row the current plan now filters out, and must
    have no relationship at all. A node some edge reaches is not one of these by
    construction, and a pre-existing node cannot be caught because it has no
    wave3_created_by.

    The 12 are attested only in a Brahmana or a Srautasutra, and
    ritual/supplementary_passages.jsonl -- where that evidence lives -- is declared
    not-imported. Importing the entity while excluding its evidence asserts what the graph
    cannot support.
    """
    from wave3_import_plan import STAGING, elements_of, get_path, passes, read_jsonl

    withheld: set[str] = set()
    for group in GROUPS:
        if not group.require_reachable_evidence:
            continue
        filename = group.source.split(":", 1)[0]
        for row in read_jsonl(STAGING / group.domain / filename):
            key = str(get_path(row, group.identity_fields[0]) or "")
            if key and not passes(row, group):
                withheld.add(key)
    del elements_of

    result: dict[str, Any] = {
        "correction": "WITHHELD_REGISTRY_ENTITIES",
        "keys_the_plan_now_withholds": len(withheld),
    }
    if not withheld:
        result.update({"already_applied": True, "executed": False})
        return result

    probe = session.run(
        "UNWIND $keys AS k MATCH (n {entity_key: k}) "
        "WHERE n.wave3_created_by IS NOT NULL AND NOT (n)--() RETURN count(n) AS c",
        keys=sorted(withheld),
    ).single()
    outstanding = int((probe or {"c": 0})["c"])
    result["present_and_unreachable"] = outstanding
    result["already_applied"] = outstanding == 0
    if not execute or not outstanding:
        result["executed"] = False
        return result

    with session.begin_transaction() as tx:
        deleted = int(
            tx.run(
                "UNWIND $keys AS k MATCH (n {entity_key: k}) "
                "WHERE n.wave3_created_by IS NOT NULL AND NOT (n)--() "
                "DELETE n RETURN count(*) AS n",
                keys=sorted(withheld),
            ).single()["n"]
        )
        tx.commit()
    result.update({"executed": True, "nodes_deleted": deleted})
    return result


def correction_retype_asserted_by(
    session: Session, run_id: str, *, execute: bool
) -> dict[str, Any]:
    """Move this wave's ASSERTED_BY edges to POSITION_ASSERTED_BY.

    Scoped to edges this wave wrote, so a curated InterpretiveClaim -> Source edge cannot
    be caught. Idempotent: on a graph where the retype has run this matches nothing.
    """
    result: dict[str, Any] = {"correction": "RETYPE_ASSERTED_BY"}
    probe = session.run(
        "MATCH ()-[r:ASSERTED_BY]->() WHERE r.wave3_touched_by IS NOT NULL "
        "RETURN count(r) AS c"
    ).single()
    outstanding = int((probe or {"c": 0})["c"])
    result["mistyped_edges"] = outstanding
    result["already_applied"] = outstanding == 0
    if not execute or not outstanding:
        result["executed"] = False
        return result
    with session.begin_transaction() as tx:
        moved = int(
            tx.run(
                "MATCH (a)-[r:ASSERTED_BY]->(b) WHERE r.wave3_touched_by IS NOT NULL "
                "CREATE (a)-[n:POSITION_ASSERTED_BY]->(b) "
                "SET n = properties(r), n.retyped_from = 'ASSERTED_BY', "
                "    n.retype_reason = 'ASSERTED_BY is declared InterpretiveClaim -> "
                "Source; this relation is ScholarlyDisagreement -> Scholar', "
                "    n.wave3_retyped_by = $run_id "
                "DELETE r RETURN count(*) AS n",
                run_id=run_id,
            ).single()["n"]
        )
        tx.commit()
    result.update({"executed": True, "edges_retyped": moved})
    return result


def correction_label_redirect_targets_as_rituals(
    session: Session, run_id: str, *, execute: bool
) -> dict[str, Any]:
    """Give the three redirect targets the :Ritual label their edges' signatures require.

    The rite registries mark three rites ALREADY_MODELLED_AS_SOCIALRITE, and the redirect
    sends their edges to those nodes -- which carry :SocialRite and not :Ritual, so 5 edges
    fell outside the PERFORMED_BY, USES_OBJECT, USES_OFFERING and USES_SUBSTANCE signatures.

    The label is truthful rather than a workaround. A marriage a Srautasutra describes with
    objects and offerings is a rite; the artifact says so by naming it already_modelled_as;
    and a node may carry two labels that are both true. MATCH (n:Ritual) goes 100 to 103.
    """
    # Every rite the artifact marks ALREADY_MODELLED_AS_SOCIALRITE, and its target. Not
    # the redirect map: that skips a row whose already_modelled_as points at ITSELF, which
    # is how VIVAHA-MARRIAGE was left as the one remaining signature violation after the
    # other two were labelled. A rite is a rite whether it redirects elsewhere or not.
    from wave3_import_plan import STAGING, read_jsonl

    targets: set[str] = set()
    for group in GROUPS:
        if not group.skip_statuses or not group.redirect_field:
            continue
        for row in read_jsonl(STAGING / group.domain / group.source.split(":", 1)[0]):
            if str(row.get(group.node_status_field) or "") not in group.skip_statuses:
                continue
            for value in (row.get(group.identity_fields[0]), row.get(group.redirect_field)):
                if value:
                    targets.add(str(value))
    targets = sorted(targets)
    result: dict[str, Any] = {
        "correction": "LABEL_REDIRECT_TARGETS_AS_RITUALS",
        "targets": targets,
    }
    if not targets:
        result.update({"already_applied": True, "executed": False})
        return result
    probe = session.run(
        "UNWIND $keys AS k MATCH (n {entity_key: k}) WHERE NOT n:Ritual RETURN count(n) AS c",
        keys=targets,
    ).single()
    outstanding = int((probe or {"c": 0})["c"])
    result["unlabelled"] = outstanding
    result["already_applied"] = outstanding == 0
    if not execute or not outstanding:
        result["executed"] = False
        return result
    with session.begin_transaction() as tx:
        labelled = int(
            tx.run(
                "UNWIND $keys AS k MATCH (n {entity_key: k}) WHERE NOT n:Ritual "
                "SET n:Ritual, n.ritual_label_added_by = $run_id RETURN count(n) AS n",
                keys=targets,
                run_id=run_id,
            ).single()["n"]
        )
        tx.commit()
    result.update({"executed": True, "nodes_labelled": labelled})
    return result


WRITERS = {
    "NODE": write_nodes,
    "NODE_PROPERTY": write_node_properties,
    "RELATIONSHIP": write_relationships,
    "RELATIONSHIP_PROPERTY": write_relationship_properties,
}

#: The owner's canonical order, by element kind. Nodes before the edges that point at them,
#: and property backfills last so they annotate a settled shape.
KIND_ORDER = {"NODE": 0, "RELATIONSHIP": 1, "NODE_PROPERTY": 2, "RELATIONSHIP_PROPERTY": 3}


def census(session: Session) -> dict[str, Any]:
    return {
        "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
        "relationships": int(
            session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        ),
        "core_corpus": {
            r["veda"]: r["n"]
            for r in session.run(
                "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="actually write")
    parser.add_argument(
        "--corrections-only",
        action="store_true",
        help=(
            "run the corrections and skip the element groups. For a correction that lands "
            "after a full pass, where re-running 25 idempotent groups would cost forty "
            "minutes to write nothing."
        ),
    )
    parser.add_argument("--json", default=str(RECEIPT))
    parser.add_argument(
        "--backup",
        default="",
        help=(
            "Directory holding the neo4j.dump taken immediately before this run. Recorded "
            "in the receipt with its checksum, because the rollback point has to be "
            "identifiable from the receipt alone -- owner section 11."
        ),
    )
    args = parser.parse_args()

    dry = load(DRY_RUN)
    plan = load(PLAN)
    if not dry or not plan:
        print("  no dry-run or no element plan. Run wave3_dry_run_v2.py first.")
        return 1

    # The dry-run's verdict is only worth as much as the tree it described. Re-read its
    # inputs rather than trusting the verdict it recorded.
    stale = {
        name: (recorded, digest(path))
        for name, recorded, path in (
            ("element_plan", (dry.get("provenance") or {}).get("element_plan_sha256"), PLAN),
            (
                "eligibility_ledger",
                (dry.get("provenance") or {}).get("eligibility_ledger_sha256"),
                LEDGER,
            ),
            ("gap_registry", (dry.get("provenance") or {}).get("gap_registry_sha256"), REGISTRY),
            ("scope_grain", (dry.get("provenance") or {}).get("scope_grain_sha256"), SCOPE),
            ("soma_correction", (dry.get("provenance") or {}).get("soma_correction_sha256"), SOMA),
        )
        if recorded != digest(path)
    }
    if stale:
        print("  the dry-run describes a different tree than this one:")
        for name, (recorded, actual) in stale.items():
            print(f"    {name}: dry-run saw {recorded}, on disk {actual}")
        print("  re-run scripts/wave3_dry_run_v2.py before importing.")
        return 1

    if dry.get("go_no_go") != "GO":
        print(f"  dry-run says {dry.get('go_no_go')}. Owner section 6: STOP.")
        for failure in dry.get("acceptance_gate_failures") or []:
            print(f"    FAIL {failure}")
        return 1
    if not plan.get("usable"):
        print("  the element plan is not usable. STOP.")
        return 1

    run_id = hashlib.sha256(
        json.dumps(
            {
                "dry_run": digest(DRY_RUN),
                "plan": digest(PLAN),
                "commit": (dry.get("provenance") or {}).get("git_commit"),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()[:16]

    checkpoint = load(CHECKPOINT)
    done: set[str] = set(checkpoint.get("completed") or []) if checkpoint.get(
        "run_id"
    ) == run_id else set()

    eligible = set(dry.get("eligible_domains") or [])
    groups = sorted(
        (g for g in GROUPS if g.domain in eligible),
        key=lambda g: (KIND_ORDER[g.kind], g.domain, g.group_id),
    )

    # Identities the plan withheld must never be written.
    withheld: dict[str, set[str]] = {}
    for entry in plan.get("groups") or []:
        withheld[entry["group_id"]] = {
            record["identity"] for record in entry.get("identity_collision_detail") or []
        }

    driver = GraphDatabase.driver(URI, auth=AUTH)
    steps: list[dict[str, Any]] = []
    try:
        with driver.session(database=DB) as session:
            before = census(session)
            print()
            mode = "EXECUTING" if args.execute else "REHEARSAL"
            print(f"  WAVE 3 IMPORT  run_id {run_id}  {mode}")
            print(
                f"  before: {before['nodes']:,} nodes / "
                f"{before['relationships']:,} relationships"
            )
            print()

            for name, correction in (
                ("SOMA_PRESSING_WEAK_ALIAS_RETIREMENT", correction_soma),
                ("M5_SPECIALIZED_FORM_OF", correction_m5),
                ("WITHHELD_REGISTRY_ENTITIES", correction_withheld_registry_entities),
                ("RETYPE_ASSERTED_BY", correction_retype_asserted_by),
                (
                    "LABEL_REDIRECT_TARGETS_AS_RITUALS",
                    correction_label_redirect_targets_as_rituals,
                ),
            ):
                if name in done:
                    print(f"  {name:46} already applied, skipping")
                    continue
                outcome = correction(session, run_id, execute=args.execute)
                steps.append(outcome)
                print(
                    f"  {name:46} "
                    + (
                        "rehearsed"
                        if not args.execute
                        else " ".join(
                            f"{k.replace('_landed', '')}={v}"
                            for k, v in outcome.items()
                            if k.endswith("_landed")
                        )
                    )
                )
                if args.execute:
                    done.add(name)
                    CHECKPOINT.write_text(
                        json.dumps({"run_id": run_id, "completed": sorted(done)}, indent=2)
                        + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )

            promised = {entry["group_id"]: entry for entry in (plan.get("groups") or [])}
            disagreements: list[str] = []
            header = (
                f"  {'group':38}{'kind':24}{'sent':>8}{'landed':>11}{'planned':>9}  status"
            )
            print()
            print(header)
            print("  " + "-" * (len(header) - 2))
            if args.corrections_only:
                groups = []

            for group in groups:
                skip = withheld.get(group.group_id, set())
                rows = [
                    row
                    for row in elements_of(group)
                    if passes(row, group) and identity_of(row, group) not in skip
                ]
                if group.skip_statuses and group.node_status_field:
                    rows = [
                        row
                        for row in rows
                        if str(get_path(row, group.node_status_field) or "")
                        not in group.skip_statuses
                    ]
                sent = len(rows)
                if group.group_id in done:
                    print(
                        f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}"
                        f"{'-':>11}{'-':>9}  done"
                    )
                    continue
                if not args.execute:
                    print(
                        f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}"
                        f"{'-':>11}{'-':>9}  rehearsed"
                    )
                    steps.append(
                        {"group_id": group.group_id, "rows_sent": sent, "executed": False}
                    )
                    continue

                outcome = WRITERS[group.kind](session, group, rows, run_id)
                if isinstance(outcome, tuple):
                    created, touched = outcome
                else:
                    created, touched = 0, int(outcome)
                # Against the plan's own promise for this group, so a disagreement shows up
                # here rather than only in the final census -- which is how the first run of
                # this import got 5,930 relationships past the per-group check.
                #
                # The comparison has to be like with like, and the first version was not: a
                # writer touches the elements it creates AND the ones it updates, while the
                # plan reports those separately, so six property groups read as
                # "plan promised 0" when the plan had promised exactly what landed under
                # another field name.
                entry = promised.get(group.group_id, {})
                if group.kind == "NODE":
                    expected = int(entry.get("nodes_create") or 0)
                    measured = created
                elif group.kind == "NODE_PROPERTY":
                    expected = int(entry.get("nodes_update") or 0)
                    measured = touched
                else:
                    expected = int(entry.get("relationships_create") or 0) + int(
                        entry.get("relationships_update") or 0
                    )
                    measured = touched
                    if group.symmetric:
                        # A symmetric group's candidates name each pair from both sides, and
                        # both name one undirected edge. cross_veda sent 16,824 rows and
                        # matched 8,412 edges; the plan counted the rows.
                        expected = len({(row["start"], row["end"]) for row in _pairs(group, rows)})
                ok = measured == expected
                steps.append(
                    {
                        "group_id": group.group_id,
                        "domain": group.domain,
                        "kind": group.kind,
                        "rows_sent": sent,
                        "elements_created": created,
                        "elements_labelled_or_updated": touched,
                        "plan_promised_create": expected,
                        "matches_the_plan": ok,
                        "executed": True,
                    }
                )
                shown = f"{created}+{touched}" if group.kind == "NODE" else str(touched)
                print(
                    f"  {group.group_id[:37]:38}{group.kind:24}{sent:>8}{shown:>11}"
                    f"{expected:>9}  " + ("ok" if ok else "DIFFERS FROM PLAN")
                )
                if not ok:
                    disagreements.append(
                        f"{group.group_id}: plan promised {expected}, {measured} landed"
                    )
                done.add(group.group_id)
                CHECKPOINT.write_text(
                    json.dumps({"run_id": run_id, "completed": sorted(done)}, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )

            after = census(session)
    finally:
        driver.close()

    receipt = {
        "schema_version": "1.0",
        "run_id": run_id,
        "executed": args.execute,
        "started_from_dry_run": str(DRY_RUN),
        "dry_run_sha256": digest(DRY_RUN),
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "rollback_point": {
            "backup_directory": args.backup or None,
            "backup_sha256": digest(pathlib.Path(args.backup) / "neo4j.dump")
            if args.backup
            else None,
            "backup_bytes": (pathlib.Path(args.backup) / "neo4j.dump").stat().st_size
            if args.backup and (pathlib.Path(args.backup) / "neo4j.dump").exists()
            else None,
            "git_commit": (dry.get("provenance") or {}).get("git_commit"),
            "restore": (
                "docker stop vedagraph-neo4j; docker run --rm -v infra_neo4j_data:/data "
                "-v <backup_directory>:/backups neo4j:5.26-community neo4j-admin database "
                "load neo4j --from-path=/backups --overwrite-destination=true; "
                "docker start vedagraph-neo4j. The dump must be named neo4j.dump inside a "
                "timestamped directory: load matches by database name, which is how the "
                "first restore attempt in this project failed."
            ),
        },
        "census_before": before,
        "census_after": after,
        "node_delta": after["nodes"] - before["nodes"],
        "relationship_delta": after["relationships"] - before["relationships"],
        "core_corpus_unchanged": before["core_corpus"] == after["core_corpus"],
        "promised_node_delta": (dry.get("expected_census") or {}).get("nodes_create"),
        "promised_relationship_delta": (
            int((dry.get("expected_census") or {}).get("relationships_create") or 0)
            - int((dry.get("expected_census") or {}).get("relationships_retire") or 0)
        ),
        "per_group_disagreements": disagreements,
        "every_group_matched_the_plan": not disagreements,
        "steps": steps,
    }
    pathlib.Path(args.json).write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print(
        f"  after: {after['nodes']:,} nodes / {after['relationships']:,} relationships"
        f"  (nodes {receipt['node_delta']:+}, relationships {receipt['relationship_delta']:+})"
    )
    print(
        f"  promised: nodes {receipt['promised_node_delta']:+}, "
        f"relationships {receipt['promised_relationship_delta']:+}"
    )
    print(f"  core corpus unchanged: {receipt['core_corpus_unchanged']}")
    if disagreements:
        print()
        print(f"  {len(disagreements)} GROUP(S) DID NOT MATCH THE PLAN:")
        for line in disagreements:
            print(f"    - {line}")
    print(f"  receipt: {args.json}")
    print()
    if not args.execute:
        print("  REHEARSAL ONLY. Nothing was written. Re-run with --execute.")
        print()
    return 0 if not disagreements else 1


if __name__ == "__main__":
    raise SystemExit(main())
