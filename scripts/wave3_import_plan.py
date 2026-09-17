#!/usr/bin/env python3
"""The element-level Wave 3 plan: every node, relationship and property, classified.

WHY THIS EXISTS
===============

The first dry-run reported per-domain row counts and then refused to state a node or
relationship delta, on the grounds that "a row may create several relationships and no
node, or update a property with no new element. The importer must emit its own per-element
plan before this figure can be stated." That refusal was right, and this module is the
thing it was waiting for.

A staging row is an **evidence row** -- one passage's finding, with its provenance and its
gates. The graph elements live inside the row's payload and in the domain's side files. So
the plan cannot be derived from row counts by arithmetic; each element group has to be
enumerated and then resolved against the live graph, one group at a time.

WHAT A GROUP IS
===============

:class:`ElementGroup` names one artifact -- a file, or an array inside a payload -- and
says what it becomes: a node of some label, a relationship of some type, or a property
write onto an element that already exists. Each group carries the identity under which the
importer will MERGE, because that identity is what decides CREATE against UPDATE, and
getting it wrong is how a MERGE silently collapses two rows into one.

The groups are data rather than code so the plan can be read without reading a planner.

COVERAGE IS MEASURED, NOT ASSUMED
=================================

Every ``.jsonl`` in an eligible domain must be claimed by a group or listed by name as
deliberately not imported, with a reason. A planner that quietly ignored a file would
under-report the plan and the import would then write less than the dry-run promised, or
more. ``unmapped_artifacts`` must be empty for the plan to be usable, and the reasons are
checked against the files that exist rather than remembered.

NOTHING IS WRITTEN
==================

The session runs MATCH and RETURN only, and that is asserted rather than intended: the
planner never builds a write clause, and the one helper that touches the driver takes a
read query and a parameter map.

Usage:
    python scripts/wave3_import_plan.py [--json OUT] [--domain NAME]
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import os
import pathlib
import sys
from typing import Any, Literal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase, Session

STAGING = pathlib.Path("data/staging")
LEDGER = STAGING / "integration" / "wave3_eligibility.json"
OVERLAYS = STAGING / "lead_overlays" / "wave1_decisions.json"
OUT = STAGING / "integration" / "wave3_import_plan.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

Kind = Literal["NODE", "RELATIONSHIP", "NODE_PROPERTY", "RELATIONSHIP_PROPERTY"]

#: Endpoints are matched on ``:Passage``, never ``:Mantra``, and the reason is measured
#: rather than stylistic: the unique index is ``passage_canonical_key_unique`` on
#: ``:Passage(canonical_key)`` and there is no index on ``:Mantra``. A Mantra-labelled
#: probe therefore scans all 20,210 Mantra nodes per element, which took 23 seconds per
#: 2,000 pairs before this was changed. Every :Mantra is a :Passage, so the probe is no
#: weaker -- and where a group must be Mantra-only, the artifact's own keys enforce it.


@dataclasses.dataclass(frozen=True)
class ElementGroup:
    """One artifact, and what it becomes in the graph."""

    group_id: str
    domain: str
    kind: Kind
    #: Relative to the domain directory. ``rows.jsonl:payload.field`` reads an array out of
    #: each row's payload instead of treating the file's lines as elements.
    source: str
    #: Node label, or relationship type. Reported so a plan can be read as a schema diff.
    element: str
    #: Fields that identify the element. For a relationship, ``(start, type, end)``.
    identity_fields: tuple[str, ...]
    #: Where the element's endpoints come from, for a relationship group.
    start_field: str | None = None
    end_field: str | None = None
    #: The label the endpoints are matched under, so a dangling reference is detectable.
    start_label: str | None = None
    end_label: str | None = None
    #: The property the endpoint field matches on. Passages join on ``canonical_key``,
    #: enrichment entities on ``entity_key`` or their own id property.
    start_key_property: str = "canonical_key"
    end_key_property: str = "canonical_key"
    #: A row is a candidate only when this passes. Written as a field/value pair rather
    #: than a lambda so the filter is visible in the emitted plan.
    require: tuple[tuple[str, Any], ...] = ()
    #: Property the element is matched on, for a NODE or *_PROPERTY group.
    match_property: str = "entity_key"
    #: Fields whose value may legitimately differ between two rows claiming one identity.
    #: One rite performed by one role, attested in two Vedic schools, is two evidence rows
    #: for ONE edge -- the graph cannot hold two edges of a type between two nodes without
    #: modelling them as such, so the importer merges their citations. Declaring the
    #: evidence fields lets that case be told apart from a real conflict, where two rows
    #: disagree about something the element asserts. Without the distinction every
    #: multi-source attestation reads as a defect.
    evidence_fields: tuple[str, ...] = ()
    #: Which field carries the relationship's object, chosen per predicate. Used where one
    #: file covers several predicates that each name their object differently.
    object_field_by_predicate: tuple[tuple[str, str], ...] = ()
    #: Field carrying the artifact's own belief about whether the element already exists.
    #: Checked against the graph, because three ritual registries were measured wrong: 16
    #: rows marked PROPOSED_NEW already exist and 3 marked EXISTING do not.
    node_status_field: str = ""
    #: True where the relation is stored once and read in both directions. Only the
    #: parallel family and the shared-formula relation are: the parallel layer is stored in
    #: ascending Veda-code order and is explicitly not a claim about which text came first.
    #: The default is DIRECTED, and the distinction is load-bearing for the plan's honesty --
    #: normalising direction on a directed relation reports an existing reversed edge as an
    #: update, and the importer's MERGE then creates a second edge the dry-run did not
    #: promise. Plan and import have to agree about direction or the delta is fiction.
    symmetric: bool = False
    #: The knowledge layer this group's elements sit in, for the groups whose side file
    #: states none. ``QualityTier`` is "a function of layer, not of confidence", so the tier
    #: follows from this through the ontology's own TIER_BY_LAYER. Left empty where the row
    #: carries its own ``evidence_layer``, which is the majority.
    knowledge_layer: str = ""
    #: The field a reader should see as this element's name. The graph gives every
    #: non-Internal node a display_label and the scorecard gates on it.
    display_label_field: str = ""
    #: Withhold an element whose evidence this wave does not import. See :func:`passes`.
    require_reachable_evidence: bool = False
    #: Statuses that mean "do not create this element", with the field naming what it is
    #: already modelled as. Three rites are ALREADY_MODELLED_AS_SOCIALRITE: VIVAHA-MARRIAGE
    #: under its own key, PITRMEDHA as PITRYANA-FUNERARY-RITE and GRHAPRAVESA as
    #: SALA-HOUSE-BUILDING. Two of those three keys are absent from the graph, so treating
    #: the status as ordinary would have created two duplicate rite nodes for rites the
    #: graph already holds under another name.
    skip_statuses: tuple[str, ...] = ()
    redirect_field: str = ""
    #: Name the node group whose minted key this relationship's start is. The start key is
    #: then computed exactly as that group mints it, rather than read from a row field: a
    #: claim or verdict has no key in its artifact, so the only way to address it is to mint
    #: the same string the node group did.
    start_minted_by: str = ""
    #: True when the element has no key of its own in the artifact and the importer mints
    #: one from the identity. Such an element cannot already exist under that key, so every
    #: distinct identity is a create -- and idempotency then rests on the minting being
    #: deterministic, which the importer must assert rather than assume.
    key_minted_from_identity: bool = False
    notes: str = ""


#: Files in an eligible domain that are deliberately NOT imported, with the reason. Checked
#: against the directory, so a stale entry is a finding rather than dead weight.
NOT_IMPORTED: dict[str, str] = {
    "communities/rejected.jsonl": "rejected candidates; the record of what was refused",
    "communities/sources.jsonl": "source descriptors, already registered",
    "cross_veda/rejected.jsonl": "13,189 refused pairs; the refusal record",
    "cross_veda/sources.jsonl": "source descriptors, already registered",
    "formula/rejected.jsonl": "14,574 refused occurrences",
    "formula/rejected_pairs.jsonl": "2,071 refused pairs",
    "formula/sources.jsonl": "source descriptor, already registered",
    "quality/rejected.jsonl": "2,127 rows outside the reference set",
    "quality/sources.jsonl": "source descriptors, already registered",
    "ritual/rejected.jsonl": "47 refused rows",
    "ritual/sources.jsonl": "20 source descriptors, already registered",
    "ritual/unresolved.jsonl": (
        "7,851 citations that resolve to no canonical passage. Deliberately withheld: an "
        "unresolved citation imported as an edge would assert an address the source does "
        "not support"
    ),
    "ritual/supplementary_passages.jsonl": (
        "12,393 Srautasutra and Grhyasutra passages. Out of Wave 3 scope: these are a new "
        "corpus rather than an enrichment of the four Samhitas, and ingesting them is a "
        "corpus decision with its own rights and recension questions"
    ),
    "ritual/works.jsonl": (
        "18 supplementary works, which exist only to hold the supplementary passages above"
    ),
    "communities/rows.jsonl": (
        "1,185 per-sukta evidence rows behind the 12 community artifacts. Evidence, not "
        "elements: the community is the element and the rows are what it was computed from"
    ),
    "formula/rows.jsonl": (
        "11,181 evidence rows. Every element the domain produces is in its side files -- "
        "relations, shares_formula_with, formula_families, nesting, match levels"
    ),
    "ritual/rows.jsonl": (
        "3,045 evidence rows recording which supplementary work cites which Samhita "
        "passage. The elements are in rites, steps, rite_edges and role_assignments"
    ),
    # CORRECTED: this entry was wrong and it is the reason GAP-SEMANTICS-001 stayed open.
    # The rows are not evidence for the fillers -- they CARRY the 30,274 assertions, and
    # the fillers are elements of those. Filing them here left the role layer imported and
    # the assertion layer it belongs to absent, so 2,052 fillers hung off passages that
    # hold no assertion at all. Retained as a NOT_IMPORTED key only so the stale-entry
    # check still sees the file; the assertions themselves are imported by the
    # SR_SEMANTIC_ASSERTION_NODES group from
    # data/staging/final_closure_sprint/agent3/semantic_assertions.jsonl, which is the
    # same rows projected one assertion per line.
    "semantic_roles/rows.jsonl": (
        "14,235 rows carrying 30,274 assertions, imported in projected form from "
        "data/staging/final_closure_sprint/agent3/semantic_assertions.jsonl rather than "
        "from this file directly; this file also carries the row-level provenance and the "
        "withheld counts, which are evidence"
    ),
    "scholarship/rejected.jsonl": "2,348 refused extractions",
    "scholarship/sources.jsonl": "13 source descriptors, already registered",
    "semantic_roles/rejected.jsonl": "5,975 refused rows",
    "semantic_roles/sources.jsonl": "source descriptors, already registered",
    "semantic_roles/role_candidates.jsonl": (
        "15,704 rows, every one importable:false. The verification queue, not a weaker "
        "grade of fact"
    ),
}


GROUPS: tuple[ElementGroup, ...] = (
    # ---- semantic_roles: migration M1's new elements ---------------------------------
    ElementGroup(
        group_id="SR_ROLE_FILLER_NODES",
        display_label_field="surface",
        domain="semantic_roles",
        kind="NODE",
        source="role_fillers.jsonl",
        element="RoleFiller",
        identity_fields=("role_filler_key",),
        match_property="role_filler_key",
        require=(("importable", True),),
        notes=(
            "Migration M1. A role occurrence in an assertion, not a copy of a canonical "
            "entity. No :RoleFiller label exists in the graph, so every one is a create."
        ),
    ),
    ElementGroup(
        group_id="SR_ASSERTION_ROLE_EDGES",
        # the role occurrence is read off a published treebank's dependency labels, which is a
        # derivation from an annotation rather than a statement about this passage
        knowledge_layer="DETERMINISTIC_DERIVED",
        domain="semantic_roles",
        kind="RELATIONSHIP",
        source="role_fillers.jsonl",
        element="ASSERTION_ROLE",
        identity_fields=("assertion_key", "role_filler_key"),
        start_field="assertion_key",
        end_field="role_filler_key",
        start_label="SemanticAssertion",
        start_key_property="assertion_key",
        end_label="RoleFiller",
        end_key_property="role_filler_key",
        require=(("importable", True),),
        notes=(
            "CORRECTED. This group previously read start_label='Passage' with a note saying "
            "'the importer resolves the ordinal to the assertion'. Nothing resolved it: the "
            "assertion nodes were never imported, because semantic_roles/rows.jsonl was "
            "filed under NOT_IMPORTED as evidence when it in fact carries the assertions. "
            "All 2,052 edges therefore landed on a :Passage, and migration card M1's own "
            "test -- 'every :RoleFiller resolves to exactly one :SemanticAssertion' -- "
            "measured 0 of 2,052 live. "
            "The assertion key is not invented: role_filler_key is "
            "'{canonical_key}:A{ordinal:03d}:R{n:02d}', so the assertion segment is read "
            "back out of a key the artifact already ships. This group is only valid "
            "alongside the SemanticAssertion node group and the corrected "
            "RELATIONSHIP_SIGNATURES[ASSERTION_ROLE] in vedagraph.domain.ontology, which "
            "now reads SemanticAssertion -> RoleFiller as card M1 declared."
        ),
    ),
    ElementGroup(
        group_id="SR_ROLE_FILLER_ENTITY_EDGES",
        # the referent is resolved from the filler's lemma against the entity registries
        knowledge_layer="DETERMINISTIC_DERIVED",
        domain="semantic_roles",
        kind="RELATIONSHIP",
        source="role_fillers.jsonl",
        element="REFERS_TO",
        identity_fields=("role_filler_key", "entity_key"),
        start_field="role_filler_key",
        end_field="entity_key",
        start_label="RoleFiller",
        end_label=None,
        start_key_property="role_filler_key",
        end_key_property="entity_key",
        require=(("importable", True),),
        notes=(
            "Only for fillers that resolve to a canonical entity. The endpoint is matched "
            "on entity_key with no label constraint, because a filler may refer to a "
            "Devata, Object, Substance, Plant, Place or Concept."
        ),
    ),
    # ---- formula ----------------------------------------------------------------------
    ElementGroup(
        group_id="FORMULA_SHARES_FORMULA_WITH",
        # two mantras share a formula because the formula layer says both contain it; nothing
        # in a source states the pair
        knowledge_layer="DETERMINISTIC_DERIVED",
        symmetric=True,
        domain="formula",
        kind="RELATIONSHIP",
        source="shares_formula_with.jsonl",
        element="SHARES_FORMULA_WITH",
        identity_fields=("a", "b"),
        start_field="a",
        end_field="b",
        start_label="Passage",
        end_label="Passage",
        notes=(
            "A new relationship type. Distinct from the existing "
            "SHARES_ENTITY_VOCABULARY_WITH, which counts shared entities rather than "
            "shared formulae."
        ),
    ),
    ElementGroup(
        group_id="FORMULA_USES_FORMULA_MATCH_LEVEL",
        domain="formula",
        kind="RELATIONSHIP_PROPERTY",
        source="uses_formula_match_level.jsonl",
        element="USES_FORMULA",
        identity_fields=("passage_key", "formula_id"),
        start_field="passage_key",
        end_field="formula_id",
        start_label="Passage",
        end_label="Formula",
        end_key_property="formula_id",
        notes=(
            "Backfills match_level onto edges that already carry their evidence under "
            "another property name. 22,686 candidates against 22,686 existing edges, so "
            "this group must resolve to updates and no creates."
        ),
    ),
    ElementGroup(
        group_id="FORMULA_NESTING_PROPERTIES",
        domain="formula",
        kind="NODE_PROPERTY",
        source="formula_nesting.jsonl",
        element="Formula",
        identity_fields=("formula_id",),
        match_property="formula_id",
        notes="Nesting typology onto the 4,825 existing :Formula nodes.",
    ),
    ElementGroup(
        group_id="FORMULA_FAMILY_PROPERTIES",
        domain="formula",
        kind="NODE_PROPERTY",
        source="formula_families.jsonl",
        element="FormulaFamily",
        identity_fields=("family_id",),
        match_property="family_id",
        notes="720 candidates against 720 existing :FormulaFamily nodes.",
    ),
    ElementGroup(
        group_id="FORMULA_RELATION_TYPOLOGY",
        symmetric=True,
        domain="formula",
        kind="RELATIONSHIP_PROPERTY",
        source="relations.jsonl",
        element="PARALLEL_FAMILY",
        identity_fields=("subject_key", "predicate", "object_key"),
        start_field="subject_key",
        end_field="object_key",
        start_label="Passage",
        end_label="Passage",
        require=(("importable", True),),
        notes=(
            "Transformation typology onto the existing parallel edges. The element is "
            "written PARALLEL_FAMILY because the row's own predicate field names which of "
            "EXACT_PARALLEL_OF, VARIANT_OF, NEAR_PARALLEL_OF or REUSES_TEXT_FROM it "
            "touches; the planner resolves the actual type per row."
        ),
    ),
    # ---- cross_veda -------------------------------------------------------------------
    ElementGroup(
        group_id="CROSS_VEDA_CONNECTION_TYPOLOGY",
        symmetric=True,
        domain="cross_veda",
        kind="RELATIONSHIP_PROPERTY",
        source="rows.jsonl:payload.established_connections",
        element="PARALLEL_FAMILY",
        identity_fields=("canonical_key", "dimension", "counterpart"),
        start_field="canonical_key",
        end_field="counterpart",
        start_label="Passage",
        end_label="Passage",
        notes=(
            "The corrected transformation typing, 396 of 6,271 types changed and 197 stored "
            "relationship types contradicted by their own text. These are property writes "
            "onto edges that already exist: each connection carries the parallel_id and the "
            "stored_match_level it was read from."
        ),
    ),
    # ---- ritual -----------------------------------------------------------------------
    ElementGroup(
        group_id="RITUAL_RITE_NODES",
        display_label_field="label_en",
        node_status_field="node_status",
        skip_statuses=("ALREADY_MODELLED_AS_SOCIALRITE",),
        redirect_field="already_modelled_as",
        domain="ritual",
        kind="NODE",
        source="rites.jsonl",
        element="Ritual",
        identity_fields=("ritual_key",),
        match_property="entity_key",
        notes=(
            "103 rites, of which the artifact marks some node_status EXISTING. The planner "
            "resolves each against the graph rather than trusting the marking."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_STEP_NODES",
        display_label_field="citation",
        domain="ritual",
        kind="NODE",
        source="steps.jsonl",
        element="RitualStep",
        identity_fields=("step_key",),
        match_property="step_key",
        notes=(
            "9,273 ordered steps, each anchored on a supplementary citation. A new label."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_RITE_EDGES",
        domain="ritual",
        kind="RELATIONSHIP",
        source="rite_edges.jsonl",
        element="RITE_PREDICATE",
        identity_fields=("ritual_key", "predicate", "object_key"),
        start_field="ritual_key",
        end_field="object_key",
        start_label=None,
        end_label=None,
        start_key_property="entity_key",
        end_key_property="entity_key",
        object_field_by_predicate=(
            ("RITE_INVOLVES_ACTION", "action_key"),
            ("USES_OBJECT", "object_key"),
            ("USES_OFFERING", "offering_key"),
            ("USES_SUBSTANCE", "material_key"),
        ),
        evidence_fields=(
            "citations",
            "co_naming_loci",
            "primary_supplementary_key",
            "quote",
            "translation",
            "veda_school",
            "evidence_source_type",
            "derivation_note",
            "mapping_confidence",
            "evidence_layer",
        ),
        notes=(
            "685 rows over four predicates, each naming its object in its own field. "
            "Endpoints are matched on entity_key with no label constraint, because a rite's "
            "object may be a Concept, Object, Substance, Offering or Action."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_ROLE_ASSIGNMENTS",
        domain="ritual",
        kind="RELATIONSHIP",
        source="role_assignments.jsonl",
        element="PERFORMED_BY",
        identity_fields=("ritual_key", "role_key"),
        start_field="ritual_key",
        end_field="role_key",
        start_key_property="entity_key",
        end_key_property="entity_key",
        evidence_fields=(
            "citations",
            "co_naming_loci",
            "primary_supplementary_key",
            "quote",
            "translation",
            "veda_school",
            "evidence_source_type",
            "derivation_note",
            "mapping_confidence",
            "evidence_layer",
        ),
        notes=(
            "179 rows binding a rite to the role that performs it. Where one rite and one "
            "role are attested in two Vedic schools the rows differ only in their evidence, "
            "and the importer merges their citations onto one edge."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_RITE_RELATIONS",
        domain="ritual",
        kind="RELATIONSHIP",
        source="rite_relations.jsonl",
        element="RITE_RITE_RELATION",
        identity_fields=("child_ritual_key", "predicate", "parent_ritual_key"),
        start_field="child_ritual_key",
        end_field="parent_ritual_key",
        start_key_property="entity_key",
        end_key_property="entity_key",
        evidence_fields=(
            "citations",
            "co_naming_loci",
            "curator_claim",
            "evidence",
            "evidence_layer",
            "evidence_source_type",
            "honesty_note",
            "mapping_confidence",
        ),
        notes=(
            "23 rite-to-rite relations, 18 PART_OF_RITE and 5 FORM_OF_RITE. The file names "
            "its endpoints child_ritual_key and parent_ritual_key; reading ritual_key and "
            "object_key gave every row a null identity and reported 2 collisions covering "
            "all 23 rows."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_ROLE_NODES",
        display_label_field="label_en",
        require_reachable_evidence=True,
        node_status_field="node_status",
        domain="ritual",
        kind="NODE",
        source="roles.jsonl",
        element="RitualRole",
        identity_fields=("role_key",),
        match_property="entity_key",
        notes=(
            "27 officiant roles, 11 marked EXISTING and 16 PROPOSED_NEW. The artifact's own "
            "note is preserved: the sixteen classical officiants are a Srautasutra schema "
            "and not a Samhita one, so in_classical_sixteen is recorded and not used as a "
            "denominator."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_ACTION_NODES",
        display_label_field="label_en",
        require_reachable_evidence=True,
        node_status_field="node_status",
        domain="ritual",
        kind="NODE",
        source="actions.jsonl",
        element="Action",
        identity_fields=("concept_key",),
        match_property="entity_key",
        notes="35 ritual actions, 9 EXISTING and 26 PROPOSED_NEW.",
    ),
    ElementGroup(
        group_id="RITUAL_IMPLEMENT_NODES",
        display_label_field="label_en",
        require_reachable_evidence=True,
        node_status_field="node_status",
        domain="ritual",
        kind="NODE",
        source="implements.jsonl",
        element="Object",
        identity_fields=("concept_key",),
        match_property="entity_key",
        notes="47 implements, 23 EXISTING and 24 PROPOSED_NEW.",
    ),
    ElementGroup(
        group_id="RITUAL_MATERIAL_NODES",
        display_label_field="label_en",
        require_reachable_evidence=True,
        node_status_field="node_status",
        domain="ritual",
        kind="NODE",
        source="materials.jsonl",
        element="Substance",
        identity_fields=("concept_key",),
        match_property="entity_key",
        notes="32 materials, every one PROPOSED_NEW.",
    ),
    ElementGroup(
        group_id="RITUAL_OFFERING_NODES",
        display_label_field="label_en",
        require_reachable_evidence=True,
        node_status_field="node_status",
        domain="ritual",
        kind="NODE",
        source="offerings.jsonl",
        element="Offering",
        identity_fields=("concept_key",),
        match_property="entity_key",
        notes="21 offerings, 8 EXISTING and 13 PROPOSED_NEW.",
    ),
    ElementGroup(
        group_id="RITUAL_DEITY_OFFERING_ATTESTATION",
        domain="ritual",
        kind="NODE_PROPERTY",
        source="deity_offerings.jsonl",
        element="Devata",
        identity_fields=("devata_key",),
        match_property="entity_key",
        notes=(
            "27 deities attested in a dative offering formula, with their loci counts. A "
            "property on the deity rather than a RECEIVES_OFFERING edge, because the rows "
            "name the deity and the dative form and NOT which offering it received -- the "
            "offering sits in surrounding sutra prose that was never parsed. An edge would "
            "have to invent the object of the verb, so the attestation is recorded and the "
            "target is not."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_STEP_EDGES",
        domain="ritual",
        kind="RELATIONSHIP",
        source="steps.jsonl",
        element="HAS_RITUAL_STEP",
        identity_fields=("ritual_key", "step_key"),
        start_field="ritual_key",
        end_field="step_key",
        start_label=None,
        end_label="RitualStep",
        start_key_property="entity_key",
        end_key_property="step_key",
        notes=(
            "9,255 steps arrived as nodes carrying a ritual_key PROPERTY and no edge, so "
            "nothing in the graph could reach them from their rite -- the readback counted "
            "them among 12,033 nodes with no relationship at all. A new predicate rather "
            "than the existing HAS_STEP, whose 3 edges point at an :Action: widening its "
            "range would change what an existing predicate means, which the acceptance "
            "gate forbids without a card."
        ),
    ),
    # ---- scholarship ------------------------------------------------------------------
    ElementGroup(
        group_id="SCHOLARSHIP_SCHOLAR_NODES",
        display_label_field="name",
        domain="scholarship",
        kind="NODE",
        source="scholars.jsonl",
        element="Scholar",
        identity_fields=("scholar_id",),
        match_property="entity_key",
        notes="17 named scholars. A new label.",
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_WORK_NODES",
        display_label_field="title",
        domain="scholarship",
        kind="NODE",
        source="works.jsonl",
        element="ScholarlyWork",
        identity_fields=("work_id",),
        match_property="entity_key",
        notes="17 scholarly works. A new label.",
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_CLAIM_ROWS",
        display_label_field="payload.passage_citation",
        domain="scholarship",
        kind="NODE",
        source="rows.jsonl",
        element="ScholarlyDisagreement",
        identity_fields=("canonical_key", "payload.axis", "payload.row_kind"),
        match_property="entity_key",
        key_minted_from_identity=True,
        notes=(
            "113 rows, each a recorded disagreement, agreement or qualification between "
            "named asserters over a passage.\n\n"
            "NOT :InterpretiveClaim, which it was until the API suite failed. That label is "
            "a curated product object -- 6 nodes, each with an `about` enum of VEDIC_TEXT / "
            "DATASET / TRADITIONAL_APPARATUS, a `falsifier`, a `claim_text` and a "
            "`claim_id`, all of which /insights promises. These rows carry `axis` and "
            "`row_kind` instead, so putting them under that label made the endpoint return "
            "`about: None` against its own schema. Adding rows to an existing label without "
            "meeting its contract is the same error as widening a predicate's range without "
            "a card."
        ),
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_CLAIM_EDGES",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="SCHOLARLY_CLAIM_ABOUT",
        identity_fields=("canonical_key", "payload.axis", "payload.row_kind"),
        start_field="canonical_key",
        end_field="canonical_key",
        start_label="ScholarlyDisagreement",
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes=(
            "113 claims arrived unattached. A new predicate, named for the relation rather "
            "than for a label that turned out to be the wrong one: the existing "
            ":InterpretiveClaim edges are SUPPORTED_BY to a Passage, meaning the passage "
            "supports the claim, and CONCERNS to a Work or Concept. Neither says 'this "
            "claim is about this passage', and reusing either would change its meaning."
        ),
    ),
    ElementGroup(
        group_id="QUALITY_VERDICT_EDGES",
        domain="quality",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="QUALITY_VERDICT_ABOUT",
        identity_fields=("canonical_key", "algorithm_version", "payload.reference_set_type"),
        start_field="canonical_key",
        end_field="canonical_key",
        start_label="QualityVerdict",
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        start_minted_by="QUALITY_VERDICT_NODES",
        require=(("mapping_confidence", "EXACT"),),
        notes=(
            "2,568 verdicts arrived unattached. Modelled on the QA_ISSUE_ON precedent -- "
            "(:QAIssue)-[:QA_ISSUE_ON]->(:Work), 915 edges -- with the verdict pointing at "
            "what it judges. The verdict is strictly about EDGES on the passage rather than "
            "the passage itself; the passage is the addressable approximation and the "
            "verdict's layers_present property says which layers it judged."
        ),
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_ASSERTED_BY_A",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="POSITION_ASSERTED_BY",
        identity_fields=("canonical_key", "payload.axis", "payload.position_a.asserter_id"),
        start_field="canonical_key",
        end_field="payload.position_a.asserter_id",
        start_label="ScholarlyDisagreement",
        end_label="Scholar",
        start_key_property="entity_key",
        end_key_property="entity_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes=(
            "The first of two named asserters per claim. Without these the 17 :Scholar "
            "nodes are unreachable and the graph cannot answer who disagreed with whom, "
            "which is the whole substance of the domain: 91 disagreements, each with two "
            "named asserters, two page-precise locators and a stated incompatibility.\n\n"
            "POSITION_ASSERTED_BY and not the existing ASSERTED_BY, whose declared "
            "signature is InterpretiveClaim -> Source. Reusing it put 226 edges outside "
            "that signature, which the quality scorecard caught -- the same error avoided "
            "deliberately for HAS_STEP and CONCERNS and then made anyway here."
        ),
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_ASSERTED_BY_B",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="POSITION_ASSERTED_BY",
        identity_fields=("canonical_key", "payload.axis", "payload.position_b.asserter_id"),
        start_field="canonical_key",
        end_field="payload.position_b.asserter_id",
        start_label="ScholarlyDisagreement",
        end_label="Scholar",
        start_key_property="entity_key",
        end_key_property="entity_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes="The second asserter. A claim whose two asserters are the same person was "
        "already withdrawn by the domain, so a MERGE collapsing the pair cannot hide one.",
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_POSITION_WORK_A",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="POSITION_STATED_IN",
        identity_fields=("canonical_key", "payload.axis", "payload.position_a.work_id"),
        start_field="canonical_key",
        end_field="payload.position_a.work_id",
        start_label="ScholarlyDisagreement",
        end_label="ScholarlyWork",
        start_key_property="entity_key",
        end_key_property="entity_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes="Where the first position is stated. Distinct from REPORTED_IN below: the "
        "work that states a position is not the work that reports the disagreement.",
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_POSITION_WORK_B",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="POSITION_STATED_IN",
        identity_fields=("canonical_key", "payload.axis", "payload.position_b.work_id"),
        start_field="canonical_key",
        end_field="payload.position_b.work_id",
        start_label="ScholarlyDisagreement",
        end_label="ScholarlyWork",
        start_key_property="entity_key",
        end_key_property="entity_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes="Where the second position is stated.",
    ),
    ElementGroup(
        group_id="SCHOLARSHIP_REPORTED_IN",
        domain="scholarship",
        kind="RELATIONSHIP",
        source="rows.jsonl",
        element="REPORTED_IN",
        identity_fields=("canonical_key", "payload.axis", "payload.witness.work_id"),
        start_field="canonical_key",
        end_field="payload.witness.work_id",
        start_label="ScholarlyDisagreement",
        end_label="ScholarlyWork",
        start_key_property="entity_key",
        end_key_property="entity_key",
        start_minted_by="SCHOLARSHIP_CLAIM_ROWS",
        notes=(
            "The work that REPORTS the disagreement, which is a different claim from "
            "stating a position in it. 73 rows are typed "
            "ASCRIPTION_DISPUTED_BY_THE_REPORTING_SOURCE precisely because the reporter and "
            "the asserter are not the same voice, and collapsing the two edges would erase "
            "that distinction."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_ATTESTATION_EDGES",
        # the attestation example is a locator the registry read out of the Samhita
        knowledge_layer="SOURCE_EXPLICIT",
        domain="ritual",
        kind="RELATIONSHIP",
        source="rites.jsonl!flatten:ritual_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("ritual_key", "value"),
        start_field="ritual_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes=(
            "The Saṃhitā attestation the registries already measured, as an edge instead of "
            "a JSON property. 1,266 (entity, passage) pairs across 153 entities, and it is "
            "what makes 17 of the 31 unreachable registry entities reachable. Rites only: "
            "the other five registries are flattened by the sibling groups below."
        ),
    ),
    ElementGroup(
        group_id="RITUAL_ROLE_ATTESTATION",
        knowledge_layer="SOURCE_EXPLICIT",  # as RITUAL_ATTESTATION_EDGES
        domain="ritual",
        kind="RELATIONSHIP",
        source="roles.jsonl!flatten:role_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("role_key", "value"),
        start_field="role_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes="Saṃhitā attestation for roles.jsonl, same contract as the rites group.",
    ),
    ElementGroup(
        group_id="RITUAL_ACTION_ATTESTATION",
        knowledge_layer="SOURCE_EXPLICIT",  # as RITUAL_ATTESTATION_EDGES
        domain="ritual",
        kind="RELATIONSHIP",
        source="actions.jsonl!flatten:concept_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("concept_key", "value"),
        start_field="concept_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes="Saṃhitā attestation for actions.jsonl, same contract as the rites group.",
    ),
    ElementGroup(
        group_id="RITUAL_IMPLEMENT_ATTESTATION",
        knowledge_layer="SOURCE_EXPLICIT",  # as RITUAL_ATTESTATION_EDGES
        domain="ritual",
        kind="RELATIONSHIP",
        source="implements.jsonl!flatten:concept_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("concept_key", "value"),
        start_field="concept_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes="Saṃhitā attestation for implements.jsonl, same contract as the rites group.",
    ),
    ElementGroup(
        group_id="RITUAL_MATERIAL_ATTESTATION",
        knowledge_layer="SOURCE_EXPLICIT",  # as RITUAL_ATTESTATION_EDGES
        domain="ritual",
        kind="RELATIONSHIP",
        source="materials.jsonl!flatten:concept_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("concept_key", "value"),
        start_field="concept_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes="Saṃhitā attestation for materials.jsonl, same contract as the rites group.",
    ),
    ElementGroup(
        group_id="RITUAL_OFFERING_ATTESTATION",
        knowledge_layer="SOURCE_EXPLICIT",  # as RITUAL_ATTESTATION_EDGES
        domain="ritual",
        kind="RELATIONSHIP",
        source="offerings.jsonl!flatten:concept_key:samhita_attestation_examples",
        element="ATTESTED_IN",
        identity_fields=("concept_key", "value"),
        start_field="concept_key",
        end_field="value",
        start_label=None,
        end_label="Passage",
        start_key_property="entity_key",
        end_key_property="canonical_key",
        notes="Saṃhitā attestation for offerings.jsonl, same contract as the rites group.",
    ),
    # ---- communities: the artifact and its refusal, never a membership claim ---------
    ElementGroup(
        group_id="COMMUNITIES_ARTIFACT_NODES",
        # Was "community_id", which is an INTEGER in communities.jsonl, so all 12
        # :DeityCommunity nodes landed with an integer display_label (0-11). display_label
        # is the product's one universal text slot and a graph-wide toLower() over it
        # raises a Neo4j type error on an integer; two benchmark probes died on it. The
        # staging build now emits a string display_label beside the id, and the id itself
        # is untouched so identity and config hash do not move.
        display_label_field="display_label",
        domain="communities",
        kind="NODE",
        source="communities.jsonl",
        element="DeityCommunity",
        identity_fields=("community_id",),
        match_property="community_id",
        notes=(
            "12 derived communities imported AS AN ARTIFACT with their method metadata and "
            "their refusal attached, per the integration plan's phase 5. No membership "
            "relationship is planned at all: six of the twelve draw every internal edge "
            "from a single hymn and five are whole connected components, so a membership "
            "edge would present a modularity artefact as a traditional category. The 1,185 "
            "rows.jsonl rows are the per-sukta evidence behind these twelve and are not "
            "themselves elements."
        ),
    ),
    # ---- quality: the evaluation, which is a finding about the graph -----------------
    ElementGroup(
        group_id="QUALITY_VERDICT_NODES",
        display_label_field="canonical_key",
        domain="quality",
        kind="NODE",
        source="rows.jsonl",
        element="QualityVerdict",
        identity_fields=(
            "canonical_key",
            "algorithm_version",
            "payload.reference_set_type",
        ),
        match_property="entity_key",
        key_minted_from_identity=True,
        require=(("mapping_confidence", "EXACT"),),
        notes=(
            "The adjudicated reference set. A new label, and deliberately a node rather "
            "than a property on the edge it judges: of 11,210 verdicts 1,402 diverge from "
            "their own metre, 1,283 confirm only via an alias the layer judges unsound and "
            "143 are refuted, so the verdict is a claim ABOUT an edge and must stay "
            "separately addressable from it. "
            "The identity carries reference_set_type because a passage legitimately holds "
            "TWO verdicts on different evidence: an "
            "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET over the mention and concept "
            "layers, adjudicated by a published human treebank, and a "
            "DETERMINISTIC_TEXT_DERIVED_REFERENCE over HAS_CHANDAS, adjudicated by counting "
            "syllables. Keying on the passage alone merged 161 of these pairs, which would "
            "have let a syllable count overwrite a human-treebank verdict -- collapsing the "
            "one distinction this domain exists to keep."
        ),
    ),
)


#: Keys an artifact says are already modelled under a different key, mapped to that key.
#: Applied to relationship endpoints in BOTH the planner and the importer, because a
#: redirect that stops at the node group leaves the edges pointing at a key nobody created:
#: 6 rite edges named VG:CONCEPT:GRHAPRAVESA and VG:CONCEPT:PITRMEDHA, whose own keys are
#: absent because the graph holds those rites as SALA-HOUSE-BUILDING and
#: PITRYANA-FUNERARY-RITE, and their MATCH found nothing and landed nothing.
_REDIRECT_CACHE: dict[str, dict[str, str]] = {}


def redirects(domain: str) -> dict[str, str]:
    """Old key to already-modelled-as key, read from the domain's own artifacts."""
    if domain in _REDIRECT_CACHE:
        return _REDIRECT_CACHE[domain]
    mapping: dict[str, str] = {}
    for group in GROUPS:
        if group.domain != domain or not group.skip_statuses or not group.redirect_field:
            continue
        for row in read_jsonl(STAGING / domain / group.source.split(":", 1)[0]):
            status = str(row.get(group.node_status_field) or "")
            target = str(row.get(group.redirect_field) or "")
            key = str(row.get(group.identity_fields[0]) or "")
            if status in group.skip_statuses and key and target and key != target:
                mapping[key] = target
    _REDIRECT_CACHE[domain] = mapping
    return mapping


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def get_path(row: dict[str, Any], dotted: str) -> Any:
    value: Any = row
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def elements_of(group: ElementGroup) -> list[dict[str, Any]]:
    """Every candidate element the group's artifact yields, before graph resolution.

    Three source forms. ``file`` reads the file's lines as elements. ``file:dotted.path``
    reads an array out of each row. ``file!flatten:keyfield:dictfield`` flattens a dict of
    lists into one element per value -- which is the shape the ritual registries store their
    Saṃhitā attestation in, veda to passage keys, and the shape no earlier form could read.
    """
    if "!flatten:" in group.source:
        filename, spec = group.source.split("!flatten:", 1)
        keyfield, dictfield = spec.split(":", 1)
        out: list[dict[str, Any]] = []
        for row in read_jsonl(STAGING / group.domain / filename):
            nested = row.get(dictfield)
            if not isinstance(nested, dict):
                continue
            for bucket, values in sorted(nested.items()):
                for value in values if isinstance(values, list) else [values]:
                    out.append(
                        {
                            keyfield: row.get(keyfield),
                            "bucket": bucket,
                            "value": str(value),
                            "attestation_basis": dictfield,
                            "samhita_attested": row.get("samhita_attested"),
                            "existence_evidence_type": row.get("existence_evidence_type"),
                        }
                    )
        return out
    if ":" in group.source:
        filename, dotted = group.source.split(":", 1)
        rows = read_jsonl(STAGING / group.domain / filename)
        out: list[dict[str, Any]] = []
        for row in rows:
            nested = get_path(row, dotted)
            if not isinstance(nested, list):
                continue
            for item in nested:
                if isinstance(item, dict):
                    merged = dict(item)
                    # The outer row's key is the element's own subject for a payload array.
                    merged.setdefault("canonical_key", row.get("canonical_key"))
                    merged.setdefault("veda", row.get("veda"))
                    out.append(merged)
        return out
    rows = read_jsonl(STAGING / group.domain / group.source)
    return [row for row in rows if isinstance(row, dict)]


#: Keys any rite edge, role assignment or rite relation names. A registry entity a rite
#: edge references is reachable whatever its own attestation, because the edge is the
#: evidence. Computed from the artifacts so the planner and the importer agree.
_REFERENCED_CACHE: set[str] | None = None


def referenced_by_a_rite_edge() -> set[str]:
    global _REFERENCED_CACHE
    if _REFERENCED_CACHE is not None:
        return _REFERENCED_CACHE
    keys: set[str] = set()
    root = STAGING / "ritual"
    for filename, fields in (
        (
            "rite_edges.jsonl",
            ("ritual_key", "action_key", "object_key", "offering_key", "material_key"),
        ),
        ("role_assignments.jsonl", ("ritual_key", "role_key")),
        ("rite_relations.jsonl", ("child_ritual_key", "parent_ritual_key")),
        ("steps.jsonl", ("ritual_key",)),
    ):
        for row in read_jsonl(root / filename):
            # Only rows that will actually become edges. Counting the artifact's full set
            # made 27 registry entities look reachable via rite edges the import then
            # refused as PROBABLE, and they landed as islands: 13 officiant roles, 9
            # actions, 3 objects and 2 substances whose only path into the graph was an
            # edge nobody was going to write. Reachability has to be computed over the
            # edges that will exist.
            if str(row.get("mapping_confidence") or "") in NOT_IMPORTABLE:
                continue
            for field in fields:
                value = row.get(field)
                if value:
                    keys.add(str(value))
    _REFERENCED_CACHE = keys
    return keys


#: Confidences the campaign has always treated as staged-and-not-importable. The constant
#: lived in the dry-run and was applied to every domain's rows.jsonl -- and to NONE of the
#: side files, which is where most elements actually come from. That gap imported 13,187
#: elements the ritual domain had staged PROBABLE with an explicit instruction attached:
#: "never imported as an assertion, because a sutra may mention an implement in order to
#: forbid it." Its report is blunter still -- "PROBABLE tiers exist precisely because they
#: need a human read, and none has had one" -- and it names the precedent, GAP-RITUAL-005,
#: where verse co-occurrence was once presented as an asserted relation.
#:
#: The cost was immediate and on the reader's surface: a chariot a sutra may be forbidding
#: appeared as a foremost ritual implement, reintroducing the exact ranking that had been
#: graded MISLEADING and fixed by defining an implement as an object a modelled rite uses.
NOT_IMPORTABLE: frozenset[str] = frozenset({"PROBABLE", "UNVERIFIED"})


def passes(row: dict[str, Any], group: ElementGroup) -> bool:
    # Applied to EVERY group, before anything else. A row the domain staged as
    # not-importable is not importable from a side file either.
    if str(row.get("mapping_confidence") or "") in NOT_IMPORTABLE:
        return False
    if not all(get_path(row, field) == value for field, value in group.require):
        return False
    if group.require_reachable_evidence:
        key = str(get_path(row, group.identity_fields[0]) or "")
        # Reachable means one of two things, both measurable here: a rite edge names it, or
        # it carries a Samhita attestation EXAMPLE -- a locator, not a claim to have one.
        #
        # The first version accepted the samhita_attested flag on its own, and two officiant
        # roles came through on it with no example recorded: roles.jsonl has no
        # samhita_attestation_examples field at all, which is why RITUAL_ROLE_ATTESTATION
        # finds 0 candidates. They became the scorecard's last two orphan_entities, and
        # exempting them by name was arguing with a gate rather than answering it. An entity
        # claiming attestation it cannot locate is weaker than an absent one.
        examples = row.get("samhita_attestation_examples")
        if isinstance(examples, dict):
            located = any(
                values if isinstance(values, list) else [values] for values in examples.values()
            )
        else:
            located = bool(examples)
        attested = located
        redirect = redirects(group.domain)
        if not attested and key not in referenced_by_a_rite_edge():
            if redirect.get(key, key) not in referenced_by_a_rite_edge():
                return False
    return True


def mint(group: ElementGroup, row: dict[str, Any]) -> str:
    """The key a minted-identity group gives one row.

    Keyed on the GROUP ID, not the element label. The first version used the label, so
    correcting :InterpretiveClaim to :ScholarlyDisagreement re-minted every key and the plan
    offered to create 113 nodes it already had. A label is the shape the graph gives an
    element and a correction may change it; the identity must not move underneath.
    """
    return f"{group.group_id}:{identity_of(row, group)}"


def minted_key(row: dict[str, Any], group: ElementGroup) -> str:
    """The minted key of the node group this relationship's start belongs to.

    Both ends call one function, so a change to the minting cannot reach one and not the
    other.
    """
    owner = next(g for g in GROUPS if g.group_id == group.start_minted_by)
    return mint(owner, row)


def identity_of(row: dict[str, Any], group: ElementGroup) -> str:
    """The identity the importer will MERGE on.

    Resolves the per-predicate object field, so a group covering several predicates keys
    on the field each predicate actually uses rather than on one field that is null for
    most of them.
    """
    by_predicate = dict(group.object_field_by_predicate)
    resolved = by_predicate.get(row_rel_type(row, group))
    parts: list[str] = []
    for field in group.identity_fields:
        if resolved and field == group.end_field:
            parts.append(str(get_path(row, resolved)))
        else:
            parts.append(str(get_path(row, field)))
    return "|".join(parts)


#: One pull per (label, property) pair, reused across groups. Built lazily because a probe
#: with no label cannot use an index at all: ``MATCH (n) WHERE n.entity_key = v`` scans all
#: 108,779 nodes, and asking it per value took 23 seconds per 2,000 values. One scan that
#: returns every value of the property costs the same as a single probe and answers every
#: question about it.
_KEY_CACHE: dict[tuple[str | None, str], set[str]] = {}


def key_universe(session: Session, label: str | None, prop: str) -> set[str]:
    """Every value of ``prop`` on nodes carrying ``label``. Cached. MATCH and RETURN only."""
    cache_key = (label, prop)
    if cache_key not in _KEY_CACHE:
        pattern = f"(n:{label})" if label else "(n)"
        query = f"MATCH {pattern} WHERE n.{prop} IS NOT NULL RETURN DISTINCT n.{prop} AS v"
        _KEY_CACHE[cache_key] = {str(record["v"]) for record in session.run(query)}
    return _KEY_CACHE[cache_key]


def existing_keys(session: Session, label: str | None, prop: str, values: list[str]) -> set[str]:
    """Which of ``values`` already name a node."""
    return set(values) & key_universe(session, label, prop)


def existing_pairs(
    session: Session,
    rel_types: list[str],
    start_label: str | None,
    start_prop: str,
    end_label: str | None,
    end_prop: str,
    pairs: list[tuple[str, str, str]],
    *,
    symmetric: bool,
) -> set[tuple[str, str, str]]:
    """Which ``(start, type, end)`` triples already exist.

    The whole edge set for the types in question is pulled once and the comparison is done
    here, rather than probing each candidate pair. The first version asked the database per
    pair and took 23 seconds per 2,000; the layers being checked hold at most 22,686 edges
    of one type, which is one cheap query.

    Direction is normalised only for a ``symmetric`` group. The parallel family is stored
    once in ascending Veda-code order and read undirected, so a direction-sensitive
    comparison would report half of it as missing and the import would create a second edge
    for every pair it already had. Doing the same to a DIRECTED relation makes the opposite
    error: a reversed edge reads as an update, and the importer's directed MERGE then
    creates a new one the plan did not promise.
    """
    if not pairs:
        return set()
    start_pattern = f":{start_label}" if start_label else ""
    end_pattern = f":{end_label}" if end_label else ""
    types = "|".join(sorted(set(rel_types)))
    query = (
        f"MATCH (a{start_pattern})-[r:{types}]->(b{end_pattern}) "
        f"WHERE a.{start_prop} IS NOT NULL AND b.{end_prop} IS NOT NULL "
        f"RETURN a.{start_prop} AS s, type(r) AS t, b.{end_prop} AS e"
    )
    stored: set[tuple[str, str, str]] = set()
    for record in session.run(query):
        stored.add((str(record["s"]), str(record["t"]), str(record["e"])))
        if symmetric:
            stored.add((str(record["e"]), str(record["t"]), str(record["s"])))
    return {pair for pair in pairs if pair in stored}


#: The parallel family, whose member type a row names in its own ``predicate`` or
#: ``dimension`` field rather than in the group.
PARALLEL_TYPES = ("EXACT_PARALLEL_OF", "VARIANT_OF", "NEAR_PARALLEL_OF", "REUSES_TEXT_FROM")
RITE_TYPES = (
    "USES_OBJECT",
    "USES_SUBSTANCE",
    "USES_OFFERING",
    "INVOLVES_OFFERING",
    "INVOLVES_SUBSTANCE",
    "INVOKES_DEVATA",
    "PERFORMED_BY",
    "PERFORMED_FOR",
    "HAS_STEP",
    "DESCRIBED_IN",
    "INVOLVES_RITUAL",
    "USED_FOR_RITE",
)


def row_rel_type(row: dict[str, Any], group: ElementGroup) -> str:
    """The relationship type a row asserts, when the group defers to the row."""
    if group.element == "PARALLEL_FAMILY":
        return str(row.get("predicate") or row.get("dimension") or "UNKNOWN")
    if group.element in ("RITE_PREDICATE", "RITE_RITE_RELATION"):
        return str(row.get("predicate") or "UNKNOWN")
    return group.element


def plan_group(
    session: Session,
    group: ElementGroup,
    provided: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    raw = elements_of(group)
    candidates = [row for row in raw if passes(row, group)]
    filtered_out = len(raw) - len(candidates)

    # Identity collisions: two source elements claiming one identity with different
    # content. A MERGE would silently keep whichever ran last.
    by_identity: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in candidates:
        by_identity[identity_of(row, group)].append(row)
    collisions: list[dict[str, Any]] = []
    multi_source: list[dict[str, Any]] = []
    evidence = set(group.evidence_fields)
    for identity, group_rows in sorted(by_identity.items()):
        if len(group_rows) < 2:
            continue
        # Which fields actually differ across the rows sharing this identity.
        fields = {field for row in group_rows for field in row}
        differing = {
            field
            for field in fields
            if len({json.dumps(row.get(field), sort_keys=True, default=str) for row in group_rows})
            > 1
        }
        if not differing:
            continue  # byte-identical duplicates; the MERGE is a no-op
        conflicting = sorted(differing - evidence)
        record = {
            "identity": identity,
            "count": len(group_rows),
            "differing_fields": sorted(differing),
            "conflicting_fields": conflicting,
        }
        if conflicting:
            collisions.append(record)
        else:
            multi_source.append(record)

    # An identity two rows disagree about is withheld, not merged. A MERGE keeps whichever
    # row ran last and discards the other silently, so the element is left out and the
    # disagreement is reported: 9 ritual step_keys each cover two distinct steps with
    # different text under one canonical URN and therefore one UUIDv5, and merging them
    # would lose 9 steps while every count looked plausible.
    collided = {record["identity"] for record in collisions}
    if collided:
        candidates = [row for row in candidates if identity_of(row, group) not in collided]

    result: dict[str, Any] = {
        "group_id": group.group_id,
        "domain": group.domain,
        "kind": group.kind,
        "element": group.element,
        "source": group.source,
        "identity_fields": list(group.identity_fields),
        "require": [list(pair) for pair in group.require],
        "notes": group.notes,
        "artifact_elements": len(raw),
        "filtered_out_by_require": filtered_out,
        "candidates": len(candidates),
        "candidates_before_collision_withholding": len(by_identity)
        + sum(len(rows) - 1 for rows in by_identity.values()),
        "distinct_identities": len(by_identity),
        "identity_collisions": len(collisions),
        "identity_collisions_withheld": len(collided),
        "rows_withheld_on_identity_collision": sum(
            len(by_identity[identity]) for identity in collided
        ),
        "identity_collision_detail": collisions[:10],
        "multi_source_evidence_merges": len(multi_source),
        "multi_source_detail": multi_source[:5],
        "evidence_fields_declared": list(group.evidence_fields),
    }

    if group.kind in ("NODE", "NODE_PROPERTY"):
        # A minted-key group counts distinct FULL identities, not distinct first fields.
        # Counting on the first field alone under-reported two groups whose identity is
        # composite: 113 scholarship claims read as 112 because two claims concern one
        # passage, and 2,568 quality verdicts read as 2,541 because a passage carries one
        # verdict per reference set. The minted key encodes the whole identity, so probing
        # it below counts them correctly without a separate tally.
        if group.key_minted_from_identity:
            # The minted keys are probed like any others. The first version asserted that
            # nothing could pre-exist under a minted key, which is true of a virgin graph
            # and false of a re-run: planning against an already-imported graph reported
            # 2,681 creates for 2,681 nodes that were already there, so the plan was not
            # idempotent even though the import was.
            minted = sorted({mint(group, row) for row in candidates})
            present = existing_keys(session, None, group.match_property, minted)
            result.update(
                {
                    "match_property": group.match_property,
                    "key_minted_from_identity": True,
                    "distinct_subjects": len(minted),
                    "already_present": len(present),
                    "nodes_create": len(minted) - len(present),
                    "nodes_update": len(present),
                    "subjects_absent_from_graph": [],
                    "property_writes": 0,
                    "dangling_references": 0,
                }
            )
            return result

        values = sorted({str(get_path(row, group.identity_fields[0])) for row in candidates})
        values = [v for v in values if v and v != "None"]
        present = existing_keys(session, None, group.match_property, values)

        # What the artifact believes, against what the graph holds. A wrong belief is not
        # fatal here -- the plan is built from the graph -- but it is a defect in the
        # artifact, and an importer that trusted node_status would MERGE new ritual
        # properties onto existing canonical Concepts or MATCH nothing at all.
        redirected: list[dict[str, str]] = []
        if group.node_status_field and group.skip_statuses:
            keep: list[dict[str, Any]] = []
            for row in candidates:
                if str(get_path(row, group.node_status_field) or "") in group.skip_statuses:
                    redirected.append(
                        {
                            "key": str(get_path(row, group.identity_fields[0])),
                            "status": str(get_path(row, group.node_status_field)),
                            "already_modelled_as": str(
                                get_path(row, group.redirect_field) or ""
                            ),
                            "redirect_target_present": str(
                                get_path(row, group.redirect_field) or ""
                            )
                            in key_universe(session, None, group.match_property),
                        }
                    )
                else:
                    keep.append(row)
            candidates = keep
            values = sorted({str(get_path(row, group.identity_fields[0])) for row in candidates})
            values = [v for v in values if v and v != "None"]
            present = existing_keys(session, None, group.match_property, values)
        result["elements_redirected_not_created"] = len(redirected)
        result["redirect_detail"] = redirected

        status_disagreements: list[dict[str, str]] = []
        if group.node_status_field:
            for row in candidates:
                key = str(get_path(row, group.identity_fields[0]))
                claimed = str(get_path(row, group.node_status_field) or "")
                if claimed == "PROPOSED_NEW" and key in present:
                    status_disagreements.append(
                        {"key": key, "artifact_says": claimed, "graph_says": "PRESENT"}
                    )
                elif claimed == "EXISTING" and key not in present:
                    status_disagreements.append(
                        {"key": key, "artifact_says": claimed, "graph_says": "ABSENT"}
                    )
        result["node_status_disagreements"] = len(status_disagreements)
        result["node_status_disagreement_detail"] = status_disagreements[:12]

        result.update(
            {
                "match_property": group.match_property,
                "key_minted_from_identity": False,
                "distinct_subjects": len(values),
                "already_present": len(present),
                "nodes_create": 0 if group.kind == "NODE_PROPERTY" else len(values) - len(present),
                "nodes_update": len(present),
                "subjects_absent_from_graph": (
                    sorted(set(values) - present)[:10] if group.kind == "NODE_PROPERTY" else []
                ),
                "property_writes": len(candidates) if group.kind == "NODE_PROPERTY" else 0,
                # For a property group an absent subject IS a dangling reference: there is
                # nothing to write the property onto.
                "dangling_references": (
                    len(values) - len(present) if group.kind == "NODE_PROPERTY" else 0
                ),
            }
        )
        return result

    # Relationship groups.
    assert group.start_field and group.end_field
    triples: list[tuple[str, str, str]] = []
    missing_endpoint_rows = 0
    by_predicate = dict(group.object_field_by_predicate)
    redirect = redirects(group.domain)
    redirected_endpoints = 0
    for row in candidates:
        start = (
            minted_key(row, group)
            if group.start_minted_by
            else get_path(row, group.start_field)
        )
        predicate = row_rel_type(row, group)
        # One file may cover several predicates that each name their object differently:
        # rite_edges writes action_key, object_key, offering_key and material_key under
        # RITE_INVOLVES_ACTION, USES_OBJECT, USES_OFFERING and USES_SUBSTANCE. Reading one
        # field for all of them produced 95 identity collisions whose object was None.
        end_field = by_predicate.get(predicate, group.end_field)
        end = get_path(row, end_field)
        if not start or not end:
            missing_endpoint_rows += 1
            continue
        if str(start) in redirect or str(end) in redirect:
            redirected_endpoints += 1
        left = redirect.get(str(start), str(start))
        right = redirect.get(str(end), str(end))
        if group.symmetric:
            # A symmetric relation is stored once and read both ways, and the artifacts name
            # each pair from BOTH sides -- so (A, type, B) and (B, type, A) are two rows and
            # one edge. Normalising here is what makes the plan's update count the number of
            # edges rather than the number of rows: cross_veda promised 16,824 and the graph
            # held 8,412, which is the same layer counted twice.
            left, right = sorted((left, right))
        triples.append((left, predicate, right))
    unique_triples = sorted(set(triples))

    # Endpoint existence, which is what makes a reference dangling rather than new.
    starts = sorted({t[0] for t in unique_triples})
    ends = sorted({t[2] for t in unique_triples})
    start_in_graph = existing_keys(session, group.start_label, group.start_key_property, starts)
    end_in_graph = existing_keys(session, group.end_label, group.end_key_property, ends)

    # An endpoint this same plan creates is not dangling; it is ordered. The owner's
    # canonical order puts schema and nodes before the edges that point at them for exactly
    # this reason, so a planner that called every such reference dangling would report 2,052
    # defects for a layer whose only problem is that it has not run yet. Counted separately
    # from the graph-resident endpoints so the distinction stays visible.
    provided = provided or {}
    start_from_plan = set(starts) & provided.get(group.start_key_property, set())
    end_from_plan = set(ends) & provided.get(group.end_key_property, set())
    start_present = start_in_graph | start_from_plan
    end_present = end_in_graph | end_from_plan

    dangling = [
        t for t in unique_triples if t[0] not in start_present or t[2] not in end_present
    ]
    resolvable = [t for t in unique_triples if t not in set(dangling)]
    # A pair whose endpoint does not exist YET cannot be probed for an existing edge, and
    # the edge cannot exist either, so it is a create by construction.
    awaiting_plan = [
        t
        for t in resolvable
        if t[0] in start_from_plan - start_in_graph or t[2] in end_from_plan - end_in_graph
    ]
    probeable = [t for t in resolvable if t not in set(awaiting_plan)]

    # An endpoint key that names more than one node is a defect in the plan, not only in
    # the import. A label-less MATCH binds every node carrying the key and two of them form
    # a cartesian product, so the plan counts one triple where the import writes n x m. The
    # first run of this import turned 387 intended REFERS_TO edges into 4,564 that way, and
    # the plan had promised 387 because it counted by key.
    ambiguous: list[dict[str, Any]] = []
    for side, values_for_side, prop, label in (
        ("start", starts, group.start_key_property, group.start_label),
        ("end", ends, group.end_key_property, group.end_label),
    ):
        if label or not values_for_side:
            continue
        rows_found = session.run(
            f"UNWIND $keys AS v MATCH (n) WHERE n.{prop} = v "
            "WITH v, count(n) AS c WHERE c > 1 RETURN v AS v, c AS c ORDER BY c DESC",
            keys=values_for_side,
        ).data()
        ambiguous.extend(
            {"side": side, "key": str(r["v"]), "nodes": int(r["c"])} for r in rows_found
        )

    types = sorted({t[1] for t in resolvable})
    probe_types = types or list(
        PARALLEL_TYPES if group.element == "PARALLEL_FAMILY" else (group.element,)
    )
    present_triples = (
        existing_pairs(
            session,
            probe_types,
            group.start_label,
            group.start_key_property,
            group.end_label,
            group.end_key_property,
            probeable,
            symmetric=group.symmetric,
        )
        if probeable
        else set()
    )

    creates = [t for t in resolvable if t not in present_triples]
    updates = [t for t in resolvable if t in present_triples]

    result.update(
        {
            "unique_triples": len(unique_triples),
            "rows_missing_an_endpoint_field": missing_endpoint_rows,
            "relationship_types_asserted": types,
            "dangling_references": len(dangling),
            "dangling_detail": [list(t) for t in dangling[:10]],
            "start_endpoints_absent": len(set(starts) - start_present),
            "end_endpoints_absent": len(set(ends) - end_present),
            "endpoints_provided_by_this_plan": len(start_from_plan | end_from_plan),
            "triples_awaiting_an_earlier_step": len(awaiting_plan),
            "endpoints_redirected": redirected_endpoints,
            "ambiguous_endpoint_keys": len(ambiguous),
            "ambiguous_endpoint_detail": ambiguous[:10],
            "relationships_create": 0 if group.kind == "RELATIONSHIP_PROPERTY" else len(creates),
            "relationships_update": len(updates),
            "property_writes": len(candidates) if group.kind == "RELATIONSHIP_PROPERTY" else 0,
            "expected_to_exist_but_absent": (
                len(creates) if group.kind == "RELATIONSHIP_PROPERTY" else 0
            ),
            "expected_to_exist_but_absent_detail": (
                [list(t) for t in creates[:10]] if group.kind == "RELATIONSHIP_PROPERTY" else []
            ),
        }
    )
    return result


def coverage(eligible: list[str]) -> dict[str, Any]:
    """Every .jsonl in an eligible domain must be claimed or named as not imported."""
    claimed: set[str] = set()
    for group in GROUPS:
        filename = group.source.split(":", 1)[0]
        claimed.add(f"{group.domain}/{filename}")
    on_disk: set[str] = set()
    for domain in eligible:
        directory = STAGING / domain
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.jsonl")):
            on_disk.add(f"{domain}/{path.name}")
    declared = {k for k in NOT_IMPORTED if k.split("/", 1)[0] in eligible}
    return {
        "artifacts_on_disk": len(on_disk),
        "claimed_by_a_group": sorted(claimed & on_disk),
        "declared_not_imported": sorted(declared & on_disk),
        "unmapped_artifacts": sorted(on_disk - claimed - declared),
        "stale_not_imported_entries": sorted(declared - on_disk),
        "manifests_ignored": "manifest.json and proofs/ are metadata, not elements",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    parser.add_argument("--domain", default="", help="plan one domain only")
    args = parser.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    eligible = list(ledger.get("eligible_domains") or [])
    if args.domain:
        eligible = [d for d in eligible if d == args.domain]

    groups = [g for g in GROUPS if g.domain in eligible]
    cover = coverage(eligible)

    driver = GraphDatabase.driver(URI, auth=AUTH)
    plans: list[dict[str, Any]] = []
    try:
        with driver.session(database=DB) as session:
            before_nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            before_rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
            # Two passes, in the owner's canonical order: nodes before the edges that
            # point at them. The first pass publishes every key it will create, so the
            # second can distinguish an endpoint that is missing from one that has simply
            # not been written yet.
            provided: dict[str, set[str]] = collections.defaultdict(set)
            node_groups = [g for g in groups if g.kind == "NODE"]
            other_groups = [g for g in groups if g.kind != "NODE"]

            for group in node_groups:
                plan = plan_group(session, group)
                plans.append(plan)
                # Rows the importer will skip are NOT provided by this plan. Including
                # them made the plan promise two rite nodes it then declined to create, and
                # the edges pointing at them read as resolvable when they were not.
                keys = {
                    str(get_path(row, group.identity_fields[0]))
                    for row in elements_of(group)
                    if passes(row, group)
                    and not (
                        group.skip_statuses
                        and str(get_path(row, group.node_status_field) or "")
                        in group.skip_statuses
                    )
                }
                if group.key_minted_from_identity:
                    keys = {
                        mint(group, row)
                        for row in elements_of(group)
                        if passes(row, group)
                    }
                provided[group.match_property] |= {k for k in keys if k and k != "None"}

            for group in other_groups:
                plans.append(plan_group(session, group, provided))

            # Order the report the way the groups were declared, so a reader compares it
            # against the spec rather than against the execution order.
            order = {g.group_id: i for i, g in enumerate(groups)}
            plans.sort(key=lambda p: order[p["group_id"]])
    finally:
        driver.close()

    totals = collections.Counter()
    for plan in plans:
        for field in (
            "nodes_create",
            "nodes_update",
            "relationships_create",
            "relationships_update",
            "property_writes",
            "dangling_references",
            "identity_collisions",
            "endpoints_redirected",
            "ambiguous_endpoint_keys",
            "identity_collisions_withheld",
            "rows_withheld_on_identity_collision",
            "multi_source_evidence_merges",
            "node_status_disagreements",
            "elements_redirected_not_created",
            "expected_to_exist_but_absent",
            "triples_awaiting_an_earlier_step",
        ):
            totals[field] += int(plan.get(field) or 0)

    by_domain: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for plan in plans:
        for field in ("nodes_create", "relationships_create", "property_writes"):
            by_domain[plan["domain"]][field] += int(plan.get(field) or 0)

    new_labels = sorted(
        {p["element"] for p in plans if p["kind"] == "NODE" and int(p.get("nodes_create") or 0) > 0}
    )
    new_types = sorted(
        {
            t
            for p in plans
            if p["kind"] == "RELATIONSHIP"
            for t in (p.get("relationship_types_asserted") or [])
        }
    )

    report = {
        "schema_version": "1.0",
        "mode": "PLAN_NO_WRITE",
        "eligible_domains": eligible,
        "graph_before": {"nodes": before_nodes, "relationships": before_rels},
        "coverage": cover,
        "groups": plans,
        "totals": dict(sorted(totals.items())),
        "by_domain": {k: dict(sorted(v.items())) for k, v in sorted(by_domain.items())},
        "schema_additions": {
            "node_labels_created": new_labels,
            "relationship_types_touched": new_types,
        },
        "expected_census": {
            "nodes_before": before_nodes,
            "nodes_after": before_nodes + totals["nodes_create"],
            "nodes_delta": totals["nodes_create"],
            "relationships_before": before_rels,
            "relationships_after": before_rels + totals["relationships_create"],
            "relationships_delta": totals["relationships_create"],
            "note": (
                "No group plans a retirement, so no element is removed by an ADDITION. The "
                "retirements Wave 3 makes are corrections, planned separately and named in "
                "the dry-run: the SOMA-PRESSING weak-alias retirement."
            ),
        },
        "identity_collisions_are_all_withheld": (
            totals["identity_collisions"] == totals["identity_collisions_withheld"]
        ),
        "usable": (
            not cover["unmapped_artifacts"]
            and not cover["stale_not_imported_entries"]
            and totals["dangling_references"] == 0
            and totals["ambiguous_endpoint_keys"] == 0
            and totals["identity_collisions"] == totals["identity_collisions_withheld"]
        ),
        "usable_note": (
            "An identity collision does not make the plan unusable; writing one would. "
            "Every colliding identity is withheld from the plan and reported by name, so "
            "no element with a contested identity reaches the graph and the count the "
            "import lands is exact. The owner's gate is on UNEXPLAINED collisions, and "
            "these are explained and excluded."
        ),
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  WAVE 3 ELEMENT-LEVEL PLAN -- nothing written")
    print(f"  graph before: {before_nodes:,} nodes / {before_rels:,} relationships")
    print()
    header = (
        f"  {'group':38}{'kind':24}{'cand':>7}{'n+':>7}{'n~':>7}{'r+':>7}{'r~':>7}"
        f"{'prop':>8}{'dangl':>7}{'coll':>6}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for plan in plans:
        print(
            f"  {plan['group_id'][:37]:38}{plan['kind']:24}{plan['candidates']:>7}"
            f"{int(plan.get('nodes_create') or 0):>7}{int(plan.get('nodes_update') or 0):>7}"
            f"{int(plan.get('relationships_create') or 0):>7}"
            f"{int(plan.get('relationships_update') or 0):>7}"
            f"{int(plan.get('property_writes') or 0):>8}"
            f"{int(plan.get('dangling_references') or 0):>7}"
            f"{int(plan.get('identity_collisions') or 0):>6}"
        )
    print()
    print(
        f"  TOTALS  nodes +{totals['nodes_create']:,}  rels +{totals['relationships_create']:,}"
        f"  property writes {totals['property_writes']:,}"
        f"  dangling {totals['dangling_references']:,}"
        f"  collisions {totals['identity_collisions']:,}"
        f"  ambiguous endpoints {totals['ambiguous_endpoint_keys']:,}"
    )
    print()
    print("  coverage of the eligible domains' artifacts:")
    print(f"    on disk              {cover['artifacts_on_disk']}")
    print(f"    claimed by a group   {len(cover['claimed_by_a_group'])}")
    print(f"    declared not imported{len(cover['declared_not_imported']):>4}")
    print(f"    UNMAPPED             {len(cover['unmapped_artifacts'])}")
    for name in cover["unmapped_artifacts"]:
        print(f"      - {name}")
    for name in cover["stale_not_imported_entries"]:
        print(f"      stale not-imported entry: {name}")
    print()
    census = report["expected_census"]
    print(
        f"  expected census: {census['nodes_before']:,} -> {census['nodes_after']:,} nodes, "
        f"{census['relationships_before']:,} -> {census['relationships_after']:,} relationships"
    )
    print()
    print(f"  PLAN USABLE: {report['usable']}")
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
