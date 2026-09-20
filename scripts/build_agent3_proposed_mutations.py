"""Assemble Agent 3's canonical delta proposal for lead integration.

Every node, relationship and property this agent wants written, with its exact match key,
the artifact it comes from, and the census delta it implies. Nothing here is applied:
Agent 3 has no write access to canonical Neo4j and did not take one.

The census delta is stated per group AND summed, and the summed figure is the only place
groups are added together -- a census is a count of graph objects, which is exactly the
kind of thing that may be summed. Assertion *derivations* are never summed and the
manifest keeps them apart.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"
BASELINE: Final = REPO / "data" / "staging" / "final_closure_sprint" / "baseline.json"


def _count(name: str) -> int:
    path = OUT_DIR / name
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _digest(name: str) -> str:
    return sha256((OUT_DIR / name).read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------
# The runnable statements. Every one is idempotent: a CREATE group MERGEs on its declared
# identity, so a re-run is a no-op rather than a duplicate, and a group that half-applied
# can simply be re-run.
#
# Every statement MATCHes its :Mantra rather than MERGEing it. That is the "no group may
# create a :Mantra" constraint enforced by construction -- MATCH cannot create. The cost is
# that a canonical_key with no Mantra would be silently skipped, so every group also carries
# a preflight that must return 0 BEFORE the write. All six were run against the live graph
# while this file was generated and all six returned 0.
# --------------------------------------------------------------------------------------

SEARCH_DERIVATIVE_CYPHER = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.canonical_key})
MERGE (t:TextVersion {text_id: row.text_id})
  ON CREATE SET t:Internal,
                t.passage_id = m.entity_id,
                t.text_version_id = row.text_version_id,
                t.text_role = row.text_role,
                t.language = row.language,
                t.script = row.script,
                t.text_form = row.text_form,
                t.text_nfc = row.text_nfc,
                t.text_original = row.text_original,
                t.accented = row.accented,
                t.content_sha256 = row.content_sha256,
                t.source_id = row.source_id,
                t.source_artifact_id = row.source_artifact_id,
                t.source_locator = row.source_locator,
                t.rights_status = row.rights_status,
                t.derived_from_text_version_id = row.derived_from_text_version_id,
                t.derivation_steps = row.derivation_steps,
                t.provenance = row.provenance,
                t.provenance_note = row.provenance_note
MERGE (m)-[:HAS_TEXT_VERSION]->(t)
"""

YV_UNACCENTED_CYPHER = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.canonical_key})
MERGE (t:TextVersion {text_id: row.text_id})
  ON CREATE SET t:Internal,
                t.passage_id = m.entity_id,
                t.text_version_id = row.text_version_id,
                t.text_role = row.text_role,
                t.language = row.language,
                t.script = row.script,
                t.text_form = row.text_form,
                t.text_nfc = row.text_nfc,
                t.text_original = row.text_original,
                t.accented = row.accented,
                t.content_sha256 = row.content_sha256,
                t.source_id = row.source_id,
                t.source_artifact_id = row.source_artifact_id,
                t.source_locator = row.source_locator,
                t.rights_status = row.rights_status,
                t.derived_from_text_version_id = row.derived_from_text_version_id,
                t.derivation_steps = row.derivation_steps,
                t.accent_source = row.accent_source,
                t.accent_source_note = row.accent_source_note,
                t.provenance = row.provenance
MERGE (m)-[:HAS_TEXT_VERSION]->(t)
"""

# ON MATCH deliberately writes only the projection marker. The 9,000 pre-existing edges are
# the deity-mention instrument's own and carry their own grades; this MERGE must not rewrite
# them. It marks them as part of the declared projection and leaves them otherwise untouched.
MENTIONS_LEMMA_CYPHER = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.canonical_key})
MATCH (l:Lemma {lemma: row.lemma})
MERGE (m)-[e:MENTIONS_LEMMA]->(l)
  ON CREATE SET e.occurrence_count = row.occurrence_count,
                e.knowledge_layer = row.knowledge_layer,
                e.provenance_class = row.provenance_class,
                e.evidence_basis = row.evidence_basis,
                e.attribution_precision = row.attribution_precision,
                e.quality_tier = row.quality_tier,
                e.projection_policy = row.projection_policy,
                e.annotation_provenance = row.annotation_provenance
  ON MATCH SET  e.projection_policy = row.projection_policy,
                e.projection_confirms_pre_existing_edge = true
"""

DOMAIN_ENTITY_CYPHER = """
UNWIND $rows AS row
MATCH (e:DomainEntity {entity_key: row.entity_key})
SET e.domain = row.domain,
    e.domain_count = row.domain_count,
    e.domain_provenance = row.domain_provenance,
    e.domain_basis = row.domain_basis,
    e.domain_vocabulary_version = row.domain_vocabulary_version,
    e.domain_is_human_annotation = row.domain_is_human_annotation
"""

# verb_features is a MAP in the artifact and Neo4j cannot store a map as a property, so this
# writes verb_features_json plus verb_feature_scheme and never touches the map. The two
# schemes are deliberately NOT flattened into shared scalar columns -- see the group notes.
SEMANTIC_ASSERTION_CYPHER = """
UNWIND $rows AS row
MATCH (m:Mantra {canonical_key: row.canonical_key})
MATCH (p:ActionPredicate {predicate: row.predicate})
MERGE (a:SemanticAssertion {assertion_key: row.assertion_key})
  ON CREATE SET a.canonical_key = row.canonical_key,
                a.veda = row.veda,
                a.assertion_ordinal = row.assertion_ordinal,
                a.predicate = row.predicate,
                a.predicate_status = row.predicate_status,
                a.frame = row.frame,
                a.verb_surface = row.verb_surface,
                a.verb_features_json = row.verb_features_json,
                a.verb_feature_scheme = row.verb_feature_scheme,
                a.root_label = row.root_label,
                a.role_scope = row.role_scope,
                a.role_derivation = row.role_derivation,
                a.derivation = row.derivation,
                a.roles_withheld = row.roles_withheld,
                a.roles_withheld_reason = row.roles_withheld_reason,
                a.cautions = row.cautions,
                a.asserted_role_count = row.asserted_role_count,
                a.three_slot_complete = row.three_slot_complete,
                a.evidence_layer = row.evidence_layer,
                a.source_id = row.source_id,
                a.source_snapshot = row.source_snapshot,
                a.mapping_confidence = row.mapping_confidence,
                a.algorithm_version = row.algorithm_version,
                a.config_hash = row.config_hash,
                a.code_commit = row.code_commit,
                a.provenance = row.provenance,
                a.review_state = row.review_state,
                a.human_annotated = row.human_annotated,
                a.model_assisted = row.model_assisted,
                a.projected_from_canonical_key = row.projected_from_canonical_key,
                a.projection_edge_types = row.projection_edge_types,
                a.projection_graph_score = row.projection_graph_score,
                a.projection_identity_basis = row.projection_identity_basis,
                a.independently_annotated = row.independently_annotated,
                a.is_samavedic_annotation = row.is_samavedic_annotation
MERGE (m)-[:HAS_SEMANTIC_ASSERTION]->(a)
MERGE (a)-[:ASSERTION_PREDICATE]->(p)
"""

# Two statements, deliberately separate. One statement that deleted and recreated would net
# to zero and hide a partial failure inside its own arithmetic.
ASSERTION_ROLE_DELETE_CYPHER = """
MATCH (:Passage)-[e:ASSERTION_ROLE]->(:RoleFiller)
DELETE e
"""

ASSERTION_ROLE_CREATE_CYPHER = """
UNWIND $rows AS row
MATCH (a:SemanticAssertion {assertion_key: row.assertion_key})
MATCH (f:RoleFiller {role_filler_key: row.role_filler_key})
MERGE (a)-[e:ASSERTION_ROLE]->(f)
  ON CREATE SET e.role = row.role,
                e.proposed_role = row.proposed_role,
                e.role_derivation = row.role_derivation,
                e.evidence = row.evidence,
                e.provenance = row.provenance
"""


#: One endpoint to check: the row field holding the key, the label, and the property the
#: key is matched on.
_Endpoint = tuple[str, str, str]

MANTRA_ENDPOINT: Final[_Endpoint] = ("canonical_key", "Mantra", "canonical_key")
LEMMA_ENDPOINT: Final[_Endpoint] = ("lemma", "Lemma", "lemma")
ENTITY_ENDPOINT: Final[_Endpoint] = ("entity_key", "DomainEntity", "entity_key")
PREDICATE_ENDPOINT: Final[_Endpoint] = ("predicate", "ActionPredicate", "predicate")
ASSERTION_ENDPOINT: Final[_Endpoint] = ("assertion_key", "SemanticAssertion", "assertion_key")
FILLER_ENDPOINT: Final[_Endpoint] = ("role_filler_key", "RoleFiller", "role_filler_key")


def _preflight(*endpoints: _Endpoint) -> str:
    """The number of DISTINCT endpoint keys that do not resolve. Must be 0.

    Deliberately distinct-key rather than per-row. A per-row ``NOT EXISTS`` over the lemma
    projection asks the same question 154,261 times to check 10,552 mantras and 10,031
    lemmas, and it is slow enough that a runner would be tempted to skip it -- a preflight
    nobody runs is a comment. Distinct keys give the identical guarantee: if every distinct
    key resolves then every row resolves, because a row's endpoint IS one of those keys.
    """
    blocks: list[str] = []
    for index, (field, label, prop) in enumerate(endpoints):
        alias = f"k{index}"
        blocks.append(
            f"UNWIND $rows AS row\n"
            f"WITH collect(DISTINCT row.{field}) AS keys\n"
            f"UNWIND keys AS {alias}\n"
            f"OPTIONAL MATCH (n:{label} {{{prop}: {alias}}})\n"
            f"WITH {alias} WHERE n IS NULL\n"
            f"RETURN count(*) AS missing_{label.lower()}"
        )
    if len(blocks) == 1:
        return blocks[0].replace(
            f"RETURN count(*) AS missing_{endpoints[0][1].lower()}",
            "RETURN count(*) AS unresolved_endpoints",
        )
    # Two endpoints: one statement per endpoint, both must return 0. Kept as a list so the
    # runner cannot accidentally read a two-endpoint check as a single number.
    return "\n;\n".join(blocks)

#: Indexes the MERGE keys need. Without the first, MERGE on :SemanticAssertion is a full
#: label scan per row over a label growing to 35,131. Creating an index is a schema change
#: rather than a data change and is the lead's call, but the import is not practical without
#: it. Measured: no index exists on that property, and assertion_key is present on 0 of the
#: 4,865 live assertions (they use assertion_id), so there is no collision risk, only a cost
#: one. The other five MERGE keys are already indexed: TextVersion.text_id, Lemma.lemma,
#: Passage.canonical_key, DomainEntity.entity_key and RoleFiller.role_filler_key.
REQUIRED_INDEXES: Final = [
    {
        "statement": "CREATE INDEX semantic_assertion_assertion_key IF NOT EXISTS "
        "FOR (a:SemanticAssertion) ON (a.assertion_key)",
        "required": True,
        "why": "MERGE on :SemanticAssertion(assertion_key) is a full label scan per row "
        "without it, 30,266 times over a growing label.",
    },
    {
        "statement": "CREATE INDEX action_predicate_predicate IF NOT EXISTS "
        "FOR (p:ActionPredicate) ON (p.predicate)",
        "required": False,
        "why": "Advisory. 41 nodes, so the scan is cheap, but it runs 30,266 times.",
    },
]

#: Rows per transaction. 154,261 lemma edges in one transaction will exhaust the default
#: heap. Every statement is idempotent and order-independent within its group, so chunking
#: $rows is safe and a failed chunk can be re-run.
RECOMMENDED_BATCH_SIZE: Final = 5000


def main() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    search_rows = _count("text_versions_search_derivative.jsonl")
    yv_rows = _count("text_versions_yv_unaccented_derived.jsonl")
    lemma_rows = _count("mentions_lemma_projection.jsonl")
    lemma_new = sum(
        1
        for line in (OUT_DIR / "mentions_lemma_projection.jsonl").open(encoding="utf-8")
        if line.strip() and not json.loads(line)["already_in_graph"]
    )
    domain_rows = _count("domain_entity_domains.jsonl")
    lexical_rows = _count("lexical_nonresolution_typed.jsonl")
    assertion_rows = _count("semantic_assertions.jsonl")
    role_edge_rows = _count("assertion_role_edges.jsonl")

    groups: list[dict[str, Any]] = [
        {
            "group_id": "A3_TEXT_VERSION_SEARCH_DERIVATIVE",
            "gap": "GAP-MORPHOLOGY-006",
            "operation": "CREATE",
            "kind": "NODE",
            "label": "TextVersion",
            "extra_labels": ["Internal"],
            "match_key": "text_id",
            "source_artifact": "text_versions_search_derivative.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "text_versions_search_derivative.jsonl",
            "cypher": [SEARCH_DERIVATIVE_CYPHER.strip()],
            "preflight": _preflight(MANTRA_ENDPOINT),
            "artifact_lines": search_rows,
            "rows": search_rows,
            "elements_written": {"nodes": search_rows, "relationships": search_rows},
            "expected_delta": {"nodes": search_rows, "relationships": search_rows},
            "nodes_delta": search_rows,
            "relationships_delta": search_rows,
            "attached_by": (
                "(:Mantra {canonical_key})-[:HAS_TEXT_VERSION]->"
                "(:TextVersion {text_id})"
            ),
            "notes": "RV 10,552 + SV 1,844 + YV 1,975. The Atharvaveda's existing 5,839 are "
            "untouched; post-import the SEARCH_DERIVATIVE population is 20,210 over 4 works.",
        },
        {
            "group_id": "A3_TEXT_VERSION_YV_UNACCENTED_DERIVED",
            "gap": "GAP-MORPHOLOGY-006",
            "operation": "CREATE",
            "kind": "NODE",
            "label": "TextVersion",
            "extra_labels": ["Internal"],
            "match_key": "text_id",
            "source_artifact": "text_versions_yv_unaccented_derived.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "text_versions_yv_unaccented_derived.jsonl",
            "cypher": [YV_UNACCENTED_CYPHER.strip()],
            "preflight": _preflight(MANTRA_ENDPOINT),
            "artifact_lines": yv_rows,
            "rows": yv_rows,
            "elements_written": {"nodes": yv_rows, "relationships": yv_rows},
            "expected_delta": {"nodes": yv_rows, "relationships": yv_rows},
            "nodes_delta": yv_rows,
            "relationships_delta": yv_rows,
            "attached_by": (
                "(:Mantra {canonical_key})-[:HAS_TEXT_VERSION]->"
                "(:TextVersion {text_id})"
            ),
            "notes": "The 139 Yajurvedic mantras the Wikisource unaccented witness does not "
            "cover. accent_source=DERIVED_ACCENT_STRIPPED on every row: this is our "
            "transform, not a second edition.",
        },
        {
            "group_id": "A3_MENTIONS_LEMMA_PROJECTION",
            "gap": "GAP-MORPHOLOGY-001",
            "operation": "MERGE",
            "kind": "RELATIONSHIP",
            "type": "MENTIONS_LEMMA",
            "start": "(:Mantra {canonical_key})",
            "end": "(:Lemma {lemma})",
            "match_key": ["canonical_key", "lemma"],
            "source_artifact": "mentions_lemma_projection.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "mentions_lemma_projection.jsonl",
            "cypher": [MENTIONS_LEMMA_CYPHER.strip()],
            "preflight": _preflight(MANTRA_ENDPOINT, LEMMA_ENDPOINT),
            "artifact_lines": lemma_rows,
            "rows": lemma_rows,
            "elements_written": {"relationships_merged": lemma_rows},
            "expected_delta": {"nodes": 0, "relationships": lemma_new},
            "why_rows_and_delta_differ": f"the statement MERGEs {lemma_rows} edges and "
            f"CREATES {lemma_new} of them; {lemma_rows - lemma_new} already exist and take "
            "the ON MATCH branch, which writes only the projection marker. Asserting "
            f"delta == {lemma_rows} would fail a correct import.",
            "nodes_delta": 0,
            "relationships_delta": lemma_new,
            "rows_in_artifact": lemma_rows,
            "rows_already_in_graph": lemma_rows - lemma_new,
            "notes": "The live 9,000 edges are a strict subset, verified pair-by-pair: 0 fall "
            "outside the projection, so MERGE adds and never rewrites. Zero-indegree :Lemma "
            "goes 9,992 -> 0 and distinct lemmas reached 39 -> 10,031.",
        },
        {
            "group_id": "A3_DOMAIN_ENTITY_DOMAIN",
            "gap": "GAP-SEMANTICS-005",
            "operation": "SET_PROPERTY",
            "kind": "NODE_PROPERTY",
            "label": "DomainEntity",
            "match_key": "entity_key",
            "properties": [
                "domain (list)",
                "domain_provenance",
                "domain_basis",
                "domain_vocabulary_version",
                "domain_is_human_annotation",
            ],
            "source_artifact": "domain_entity_domains.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "domain_entity_domains.jsonl",
            "cypher": [DOMAIN_ENTITY_CYPHER.strip()],
            "preflight": _preflight(ENTITY_ENDPOINT),
            "artifact_lines": domain_rows,
            "rows": domain_rows,
            "elements_written": {
                "nodes_touched": domain_rows,
                "properties": domain_rows * 6,
            },
            "expected_delta": {"nodes": 0, "relationships": 0},
            "why_rows_and_delta_differ": "a property write changes no census figure. Assert "
            "on MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e) -> 0 instead.",
            "nodes_delta": 0,
            "relationships_delta": 0,
            "properties_written": domain_rows * 6,
            "nodes_touched": domain_rows,
            "notes": "375 nodes, not the 229 the registry row's description states. "
            "domain IS NULL goes 375 -> 0; 68 are multi-domain; 350 deterministic and 25 "
            "model-assisted, typed apart. No row claims human annotation.",
        },
        {
            "group_id": "A3_LEXICAL_NONRESOLUTION_TYPED",
            "gap": "GAP-MORPHOLOGY-004",
            "operation": "NONE_ARTIFACT_ONLY",
            "kind": "ARTIFACT",
            "source_artifact": "lexical_nonresolution_typed.jsonl",
            "skip": True,
            "cypher": None,
            "parameters_from": None,
            "preflight": None,
            "artifact_lines": lexical_rows,
            "rows": 0,
            "elements_written": {"nodes": 0, "relationships": 0},
            "expected_delta": {"nodes": 0, "relationships": 0},
            "runner_instruction": "SKIP. NONE_ARTIFACT_ONLY: there is no statement to run "
            "and no element to write. Do not guess one.",
            "nodes_delta": 0,
            "relationships_delta": 0,
            "notes": "Deliberately no graph mutation. The 711 tokens are not graph objects; "
            "they are the refusal record of the lexical layer, and typing them is a change "
            "to data/knowledge/rigveda_lexical_v1's refusal file and to the policy document, "
            "both of which are tracked. 79 are Anukramani-corroborated and still get no edge.",
        },
        {
            "group_id": "A3_SEMANTIC_ASSERTION_NODES",
            "gap": "GAP-SEMANTICS-001",
            "operation": "CREATE",
            "kind": "NODE",
            "label": "SemanticAssertion",
            "match_key": "assertion_key",
            "source_artifact": "semantic_assertions.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "semantic_assertions.jsonl",
            "cypher": [SEMANTIC_ASSERTION_CYPHER.strip()],
            "preflight": _preflight(MANTRA_ENDPOINT, PREDICATE_ENDPOINT),
            "artifact_lines": assertion_rows,
            "rows": assertion_rows,
            "elements_written": {
                "nodes": assertion_rows,
                "relationships": assertion_rows * 2,
                "relationship_split": {
                    "HAS_SEMANTIC_ASSERTION": assertion_rows,
                    "ASSERTION_PREDICATE": assertion_rows,
                },
            },
            "expected_delta": {
                "nodes": assertion_rows,
                "relationships": assertion_rows * 2,
            },
            "index_required_before_this_group": REQUIRED_INDEXES[0]["statement"],
            "verb_features_is_not_written_as_a_map": "The artifact keeps verb_features as a "
            "dict for a human reader; Neo4j cannot store a map as a property, so the "
            "statement writes verb_features_json and verb_feature_scheme instead. The two "
            "schemes -- ZURICH_VEDAWEB 22,556 for RV and SV, DCS_UD 7,710 for AV and YV -- "
            "are NOT flattened into shared columns: IND and Ind are the same mood in two "
            "notations, so one verb_mood property would make WHERE verb_mood = 'IND' "
            "silently return the Rigvedic half and drop the Atharvavedic one, a filter that "
            "looks like a feature filter and is actually a corpus filter.",
            "nodes_delta": assertion_rows,
            "relationships_delta": assertion_rows * 2,
            "attached_by": [
                "(:Mantra {canonical_key})-[:HAS_SEMANTIC_ASSERTION]->"
                "(:SemanticAssertion {assertion_key})",
                "(:SemanticAssertion {assertion_key})-[:ASSERTION_PREDICATE]->"
                "(:ActionPredicate {predicate})",
            ],
            "notes": "RV 22,192 + AV 6,167 + YV 1,543 + SV 364 (SV was 372 before the 8 "
            "NEAR_PARALLEL_OF assertions were withheld to "
            "A3_SEMANTIC_ASSERTION_WITHHELD). Every predicate resolves inside the "
            "registry's closed 41. The live 4,865 keep their own derivations and are not "
            "touched; role_derivation on the new rows keeps all five instruments "
            "unsummable. Every one of these arrives review_state=UNREVIEWED, which takes "
            "GAP-SEMANTICS-002 from 4,865 to 35,131.",
        },
        {
            "group_id": "A3_SEMANTIC_ASSERTION_WITHHELD",
            "gap": "GAP-SEMANTICS-001",
            "operation": "NONE_ARTIFACT_ONLY",
            "kind": "ARTIFACT",
            "source_artifact": "semantic_assertions_withheld.jsonl",
            "skip": True,
            "cypher": None,
            "parameters_from": None,
            "preflight": None,
            "artifact_lines": _count("semantic_assertions_withheld.jsonl"),
            "rows": 0,
            "elements_written": {"nodes": 0, "relationships": 0},
            "expected_delta": {"nodes": 0, "relationships": 0},
            "runner_instruction": "SKIP. NONE_ARTIFACT_ONLY: this is the withheld queue, "
            "and writing any of it would undo the ruling. Do not guess a statement.",
            "nodes_delta": 0,
            "relationships_delta": 0,
            "notes": "8 CROSS_VEDA_TEXT_IDENTITY assertions over 5 Samavedic verses, "
            "withheld on the lead's ruling because the live graph types those 5 pairs "
            "NEAR_PARALLEL_OF while the projection asserts letter identity for them. Not "
            "deleted: a bounded evidenced queue carrying each pair's full live edge set, "
            "the same shape as the 79 Anukramani-corroborated lexical tokens. The "
            "artifact's own containment score independently agrees -- these 5 are exactly "
            "the 5 pairs of 216 scoring below 1.0.",
        },
        {
            "group_id": "A3_ASSERTION_ROLE_REANCHOR",
            "gap": "GAP-SEMANTICS-003",
            "operation": "REPLACE",
            "kind": "RELATIONSHIP",
            "type": "ASSERTION_ROLE",
            "delete_first": "(:Passage)-[:ASSERTION_ROLE]->(:RoleFiller)",
            "delete_count": 2052,
            "start": "(:SemanticAssertion {assertion_key})",
            "end": "(:RoleFiller {role_filler_key})",
            "match_key": ["assertion_key", "role_filler_key"],
            "source_artifact": "assertion_role_edges.jsonl",
            "parameters_from": "data/staging/final_closure_sprint/agent3/"
            "assertion_role_edges.jsonl",
            "preflight": _preflight(ASSERTION_ENDPOINT, FILLER_ENDPOINT),
            "preflight_depends_on_group": "A3_SEMANTIC_ASSERTION_NODES",
            "preflight_timing": "Run this preflight AFTER A3_SEMANTIC_ASSERTION_NODES and "
            "BEFORE step 2. Its :SemanticAssertion endpoints are created by that group, so "
            "run earlier it reports all 1,149 distinct assertion keys missing -- which "
            "measures the ordering, not the artifact.",
            "artifact_lines": role_edge_rows,
            "rows": role_edge_rows,
            "cypher": [
                {
                    "step": 1,
                    "name": "DELETE the mis-anchored edges",
                    "statement": ASSERTION_ROLE_DELETE_CYPHER.strip(),
                    "parameters_from": None,
                    "rows": 2052,
                    "expected_delta": {"nodes": 0, "relationships": -2052},
                    "assert_between_steps": "MATCH ()-[r:ASSERTION_ROLE]->() "
                    "RETURN count(r) -> 0",
                },
                {
                    "step": 2,
                    "name": "CREATE them on the endpoint card M1 declared",
                    "statement": ASSERTION_ROLE_CREATE_CYPHER.strip(),
                    "parameters_from": "data/staging/final_closure_sprint/agent3/"
                    "assertion_role_edges.jsonl",
                    "rows": role_edge_rows,
                    "expected_delta": {"nodes": 0, "relationships": role_edge_rows},
                    "assert_after": "MATCH (:SemanticAssertion)-[r:ASSERTION_ROLE]->"
                    "(:RoleFiller) RETURN count(r) -> 2052, and "
                    "MATCH (:Passage)-[r:ASSERTION_ROLE]->() RETURN count(r) -> 0",
                },
            ],
            "expected_delta": {"nodes": 0, "relationships": role_edge_rows - 2052},
            "why_the_two_steps_are_separate": "The group nets to 0 relationships. Run as "
            "one statement, a partial failure would net to zero by accident and look like "
            "success. Split, the intermediate count makes a half-applied group visible.",
            "nodes_delta": 0,
            "relationships_delta": role_edge_rows - 2052,
            "notes": "A replace, not an add. The live 2,052 edges start at a :Passage, which "
            "SCHEMA_MIGRATION_CARDS.md M1 never declared and which leaves every filler "
            "unresolvable to an assertion. Net relationship delta is 0: 2,052 deleted, 2,052 "
            "created on the declared endpoint. This group MUST run after "
            "A3_SEMANTIC_ASSERTION_NODES or every edge dangles.",
            "ships_with_a_code_change_and_is_invalid_without_it": {
                "file": "src/vedagraph/domain/ontology.py",
                "element": "RELATIONSHIP_SIGNATURES[ASSERTION_ROLE]",
                "was": "(Passage|Mantra) -> RoleFiller",
                "now": "SemanticAssertion -> RoleFiller",
                "why_both_or_neither": "The signature alone makes the 2,052 live edges "
                "violate it. The re-anchor alone makes 2,052 new ones violate the old "
                "signature. Agent 8 flagged the re-anchor as a scorecard blocker on the old "
                "signature and was right about the measurement; the lead ruled the "
                "signature is what drifted from owner-approved card M1, not the proposal.",
                "already_applied_in_the_working_tree": True,
                "pinned_by": "tests/domain/test_agent3_closure.py::"
                "test_the_assertion_role_signature_matches_the_migration_card",
            },
        },
    ]

    nodes_delta = sum(g["nodes_delta"] for g in groups)
    rels_delta = sum(g["relationships_delta"] for g in groups)
    proposal = {
        "artifact": "AGENT_3_PROPOSED_MUTATIONS",
        "agent": "AGENT_3_MORPHOLOGY_SEMANTICS",
        "at": datetime.now(UTC).isoformat(),
        "write_access_taken": "NONE -- every measurement was MATCH/RETURN only",
        "baseline": {
            "head": baseline["head"],
            "nodes": baseline["graph"]["nodes"],
            "relationships": baseline["graph"]["relationships"],
            "core_total": baseline["graph"]["core_total"],
        },
        "ordering": [g["group_id"] for g in groups],
        "groups": groups,
        "census_delta": {
            "nodes": nodes_delta,
            "relationships": rels_delta,
            # DELTAS ONLY, deliberately. An earlier revision of this file published
            # nodes_after and relationships_after computed against the 117,970 / 282,389
            # baseline. Three other agents' groups have landed since, so those absolutes
            # were already wrong when they were written -- and an absolute after-figure
            # computed against a stale baseline is how a correct import looks like a failed
            # one. The lead measures before each group and adds the delta.
            "absolutes_deliberately_not_published": (
                "Compute them from the graph at execution time. This file states deltas "
                "because it cannot know what has landed between generation and execution."
            ),
            "per_group": {
                g["group_id"]: g["expected_delta"] for g in groups
            },
            "core_corpus_delta": 0,
            "core_corpus_invariant": "20,210 mantras unchanged -- no group creates, deletes "
            "or relabels a :Mantra. Enforced by construction: every statement MATCHes its "
            "Mantra and MATCH cannot create.",
        },
        "execution_contract": {
            "ordering_is_binding": [g["group_id"] for g in groups],
            "skip_groups": [g["group_id"] for g in groups if g.get("skip")],
            "indexes_to_create_first": REQUIRED_INDEXES,
            "recommended_batch_size": RECOMMENDED_BATCH_SIZE,
            "per_group_protocol": [
                "1. Run the group's `preflight` with the same $rows. It must return 0. "
                "A non-zero result means an endpoint does not resolve and the write would "
                "silently skip that row rather than fail.",
                "2. Measure nodes and relationships.",
                "3. Run the group's `cypher` statements in order, chunking $rows at "
                f"{RECOMMENDED_BATCH_SIZE}. Every statement is idempotent and "
                "order-independent within its group, so a failed chunk can be re-run.",
                "4. Measure again and assert the difference equals `expected_delta`. STOP "
                "on mismatch.",
                "5. Assert the core corpus is still 20,210.",
            ],
            "rows_is_not_the_artifact_line_count": {
                "A3_MENTIONS_LEMMA_PROJECTION": f"{lemma_rows} artifact lines, "
                f"{lemma_rows} edges MERGEd, {lemma_new} CREATED. Assert the delta against "
                f"{lemma_new}, not {lemma_rows}.",
                "A3_DOMAIN_ENTITY_DOMAIN": f"{domain_rows} artifact lines, {domain_rows} "
                "nodes touched, census delta 0. A property write moves no census figure.",
                "A3_LEXICAL_NONRESOLUTION_TYPED": f"{lexical_rows} artifact lines, 0 "
                "elements written. SKIP.",
                "A3_SEMANTIC_ASSERTION_WITHHELD": "8 artifact lines, 0 elements written. "
                "SKIP.",
                "A3_ASSERTION_ROLE_REANCHOR": f"{role_edge_rows} artifact lines, "
                f"{role_edge_rows} edges created AND 2,052 deleted, net 0. Assert each step "
                "separately.",
            },
        },
        "counts_by_operation": {
            "CREATE_NODE": sum(g["nodes_delta"] for g in groups if g["operation"] == "CREATE"),
            "CREATE_RELATIONSHIP": sum(
                g["relationships_delta"]
                for g in groups
                if g["operation"] in {"CREATE", "MERGE"}
            ),
            "REPLACE_RELATIONSHIP": 2052,
            "SET_PROPERTY_NODES_TOUCHED": domain_rows,
            "DELETE_RELATIONSHIP": 2052,
        },
        "artifact_digests": {
            name: _digest(name)
            for name in sorted({g["source_artifact"] for g in groups})
        },
        "readback_tests_the_lead_must_run": {
            "GAP-MORPHOLOGY-001": (
                "MATCH (l:Lemma) WHERE size([(l)<--()|1])=0 RETURN count(l) -> 0"
            ),
            "GAP-MORPHOLOGY-004": (
                "no graph readback; the artifact and the policy document are the surface"
            ),
            "GAP-MORPHOLOGY-006": "MATCH (t:TextVersion) WHERE t.text_role='SEARCH_DERIVATIVE' "
            "RETURN count(t) -> 20210, over 4 works; and MATCH (p:Mantra {veda:'YV'}) WHERE "
            "NOT (p)-[:HAS_TEXT_VERSION]->(:TextVersion {accented:false}) RETURN count(p) -> 0",
            "GAP-SEMANTICS-001": "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() RETURN m.veda, "
            "count(DISTINCT m) -> RV 10150, AV 3295, YV 574, SV 211 (not 216: the 5 "
            "NEAR_PARALLEL_OF pairs are withheld)",
            "GAP-SEMANTICS-002": "MATCH (a:SemanticAssertion) WHERE a.review_state='UNREVIEWED' "
            "RETURN count(a) -> 35,131 after import (4,865 live + 30,266 staged), up from "
            "4,865. NOT CLOSED, and this import makes it larger.",
            "GAP-SEMANTICS-003": "MATCH (a:SemanticAssertion) WHERE "
            "size([(a)-[:ASSERTION_ROLE]->(:RoleFiller {role:'AGENT'})|1])>0 AND "
            "size([(a)-[:ASSERTION_ROLE]->(:RoleFiller {role:'PATIENT'})|1])>0 AND "
            "size([(a)-[:ASSERTION_PREDICATE]->()|1])>0 RETURN count(a) -> 341",
            "GAP-SEMANTICS-005": (
                "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e) -> 0"
            ),
        },
    }
    path = OUT_DIR / "proposed_mutations.json"
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proposal["census_delta"], indent=2))
    print(json.dumps(proposal["counts_by_operation"], indent=2))


if __name__ == "__main__":
    main()
