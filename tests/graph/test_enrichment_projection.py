"""Tests for the enrichment projection: readers, schema, and the batched MERGE loader.

Everything here runs against synthetic JSONL written into ``tmp_path`` and a fake session
that records the Cypher and parameters it was handed. No live database is required, which
is deliberate: the properties worth pinning are that a data file can never name a
relationship type, that counts are distinct edges rather than rows read, and that a row
with a missing endpoint is reported instead of dropped. All three are decidable from the
queries the loader emits and the numbers it returns, and a test that needed Neo4j running
would be skipped exactly when it was most needed.

The one test that does need a database is marked ``live`` and additionally gated on
``VEDAGRAPH_LIVE_NEO4J``, because ``pyproject.toml`` does not deselect ``live`` by default
and this file must not turn a green suite red on a machine with no Neo4j.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any

import pytest

from vedagraph.enrich.predicates import CONTROLLED_PREDICATES
from vedagraph.enrich.provenance import PIPELINE_VERSION
from vedagraph.graph import enrichment, enrichment_loader, enrichment_schema
from vedagraph.graph.enrichment_loader import (
    UncontrolledPredicateError,
    UnknownObjectKindError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RUN_ID = "vedagraph-graph-enrichment-v1:test:0000"


def _provenance(**overrides: Any) -> dict[str, Any]:
    """A provenance envelope in the shape ``Provenance.as_dict`` serializes.

    Evidence is a JSON *array* here, not a string, because that is what ``as_dict``
    produces and therefore what lands in the JSONL. The reader is responsible for
    encoding it; one test below feeds it the already-encoded form instead.
    """
    envelope: dict[str, Any] = {
        "trust": "DETERMINISTIC_DERIVED",
        "method": "test-method",
        "score": 0.9,
        "evidence": [
            {"locator": "VG:RV:1.1.1", "surface": "SCRIPT_FOLDED", "quote": "agnim ile"},
            {"locator": "VG:SV:1.1.1", "surface": "SCRIPT_FOLDED", "quote": "agnim ile"},
        ],
        "state": "ACCEPTED",
        "pipeline_version": PIPELINE_VERSION,
        "run_id": _RUN_ID,
        "model": "",
        "prompt_policy": "",
        "notes": "",
    }
    envelope.update(overrides)
    return envelope


CONCEPT_ROWS: list[dict[str, Any]] = [
    {
        "concept_id": "VG:CONCEPT:FIRE",
        "preferred_label_sa": "agni",
        "preferred_label_en": "fire",
        "node_type": "NATURAL_PHENOMENON",
        "aliases_sa": ["agni", "agní"],
        "aliases_en": ["fire", "flame"],
        "broader": [],
        "definition": "Fire as a natural phenomenon.",
        "related_devatas": ["VG:DEVATA:AGNIH"],
    },
    {
        "concept_id": "VG:CONCEPT:RITUAL_FIRE",
        "preferred_label_sa": "ahavaniya",
        "preferred_label_en": "ritual fire",
        "node_type": "RITUAL",
        "aliases_sa": [],
        "aliases_en": ["offering fire"],
        "broader": ["VG:CONCEPT:FIRE"],
        "definition": "The fire into which offerings are made.",
        "related_devatas": [],
    },
]

FORMULA_ROWS: list[dict[str, Any]] = [
    {
        "formula_id": "VG:ENRICH:FORMULA:aaaa",
        "normalized": "agnim ile purohitam",
        "display_form": "agním īḷe puróhitam",
        "word_count": 3,
        "char_count": 19,
        "occurrence_count": 7,
        "mantra_count": 5,
        "vedas": ["RV", "SV"],
        "veda_counts": {"RV": 4, "SV": 3},
        "cross_veda": True,
        "source_forms": ["agním īḷe puróhitam"],
        "derivation_method": "repeated-ngram",
        **_provenance(),
    }
]

OCCURRENCE_ROWS: list[dict[str, Any]] = [
    {
        "formula_id": "VG:ENRICH:FORMULA:aaaa",
        "passage_key": "VG:RV:1.1.1",
        "veda": "RV",
        "source_form": "agním īḷe puróhitam",
        **_provenance(),
    },
    {
        "formula_id": "VG:ENRICH:FORMULA:aaaa",
        "passage_key": "VG:SV:1.1.1",
        "veda": "SV",
        "source_form": "agnim ile purohitam",
        **_provenance(),
    },
    # Same (passage, formula) pair a second time. The stages legitimately emit this when
    # one formula is found by two derivations; MERGE collapses it and the loader must
    # report one edge, not two.
    {
        "formula_id": "VG:ENRICH:FORMULA:aaaa",
        "passage_key": "VG:SV:1.1.1",
        "veda": "SV",
        "source_form": "agnim ile purohitam",
        **_provenance(method="repeated-ngram-second-pass"),
    },
]

PARALLEL_ROWS: list[dict[str, Any]] = [
    {
        "parallel_id": "VG:ENRICH:PARALLEL:0001",
        "predicate": "EXACT_PARALLEL_OF",
        "subject_key": "VG:RV:1.1.1",
        "object_key": "VG:SV:1.1.1",
        "subject_veda": "RV",
        "object_veda": "SV",
        "veda_pair": "RV-SV",
        "match_level": "ACCENT_INSENSITIVE",
        "levels_reached": ["ACCENT_INSENSITIVE", "SCRIPT_FOLDED", "SANDHI_INSENSITIVE"],
        "similarity": 1.0,
        "token_jaccard": 1.0,
        "ngram_jaccard": 1.0,
        "lcs_ratio": 1.0,
        "edit_ratio": 1.0,
        **_provenance(score=1.0),
    },
    {
        "parallel_id": "VG:ENRICH:PARALLEL:0002",
        "predicate": "NEAR_PARALLEL_OF",
        "subject_key": "VG:RV:1.2.3",
        "object_key": "VG:AV:2.3.4",
        "subject_veda": "RV",
        "object_veda": "AV",
        "veda_pair": "AV-RV",
        "match_level": "SANDHI_INSENSITIVE",
        "levels_reached": ["SANDHI_INSENSITIVE"],
        "similarity": 0.81,
        "token_jaccard": 0.78,
        "ngram_jaccard": 0.74,
        "lcs_ratio": 0.83,
        "edit_ratio": 0.8,
        # Evidence already encoded as a JSON string, which is the shape
        # Provenance.as_edge_properties produces. Both shapes must survive the reader.
        **_provenance(
            evidence=json.dumps(
                [{"locator": "VG:RV:1.2.3", "surface": "IAST", "quote": "indra"}]
            )
        ),
    },
]

ASSERTION_ROWS: list[dict[str, Any]] = [
    {
        "assertion_id": "VG:ENRICH:CONCEPT-ASSERTION:0001",
        "passage_key": "VG:RV:1.1.1",
        "veda": "RV",
        "concept_id": "VG:CONCEPT:FIRE",
        "confidence": 0.88,
        **_provenance(),
    }
]

SEMANTIC_ROWS: list[dict[str, Any]] = [
    {
        "candidate_id": "VG:ENRICH:SEMANTIC:0001",
        "passage_key": "VG:RV:1.1.1",
        "veda": "RV",
        "predicate": "PRAISES",
        "object_kind": "COSMIC_ENTITY",
        "object_key": "VG:CONCEPT:FIRE",
        "object_label": "Agni",
        "confidence": 0.8,
        **_provenance(
            trust="LLM_EXTRACTED", state="CANDIDATE", model="test-model", prompt_policy="v1"
        ),
    },
    {
        "candidate_id": "VG:ENRICH:SEMANTIC:0002",
        "passage_key": "VG:RV:1.1.2",
        "veda": "RV",
        "predicate": "INVOKES",
        "object_kind": "DEVATA",
        "object_key": "VG:DEVATA:AGNIH",
        "object_label": "Agni",
        "confidence": 0.77,
        **_provenance(
            trust="LLM_EXTRACTED", state="CANDIDATE", model="test-model", prompt_policy="v1"
        ),
    },
]


def _write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )


@pytest.fixture
def project_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """A project root holding a complete synthetic enrichment artifact set."""
    directory = enrichment.enrichment_dir(tmp_path)
    _write_jsonl(directory / enrichment.CONCEPTS_FILE, CONCEPT_ROWS)
    _write_jsonl(directory / enrichment.FORMULAS_FILE, FORMULA_ROWS)
    _write_jsonl(directory / enrichment.FORMULA_OCCURRENCES_FILE, OCCURRENCE_ROWS)
    _write_jsonl(directory / enrichment.PARALLELS_FILE, PARALLEL_ROWS)
    _write_jsonl(directory / enrichment.CONCEPT_ASSERTIONS_FILE, ASSERTION_ROWS)
    _write_jsonl(directory / enrichment.SEMANTIC_CANDIDATES_FILE, SEMANTIC_ROWS)
    (directory / enrichment.MANIFEST_FILE).write_text(
        json.dumps({"run_id": _RUN_ID, "pipeline_version": PIPELINE_VERSION}), encoding="utf-8"
    )
    return tmp_path


class FakeSession:
    """Records every query and parameter set, and answers the merge count.

    ``merged_for`` lets a test say how many edges the database "created" for a batch, which
    is how the unmatched-endpoint arithmetic is exercised without a database that has no
    endpoints in it.
    """

    def __init__(self, merged_for: Any = None) -> None:
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []
        self._merged_for = merged_for

    def run(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = list(params.get("rows", []))
        self.calls.append((cypher, rows))
        if "AS merged" not in cypher:
            return []
        merged = len(rows) if self._merged_for is None else self._merged_for(cypher, rows)
        return [{"merged": merged}]

    @property
    def cypher(self) -> list[str]:
        return [c for c, _ in self.calls]

    def rows_for(self, needle: str) -> list[dict[str, Any]]:
        return [row for c, rows in self.calls if needle in c for row in rows]


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def test_concept_nodes_keep_aliases_as_string_arrays(project_root: pathlib.Path) -> None:
    nodes = {n["concept_id"]: n for n in enrichment.iter_concept_nodes(project_root)}
    assert set(nodes) == {"VG:CONCEPT:FIRE", "VG:CONCEPT:RITUAL_FIRE"}
    fire = nodes["VG:CONCEPT:FIRE"]
    assert fire["aliases_sa"] == ["agni", "agní"]
    assert fire["aliases_en"] == ["fire", "flame"]
    assert fire["node_type"] == "NATURAL_PHENOMENON"


def test_concept_nodes_omit_fields_that_are_edges(project_root: pathlib.Path) -> None:
    for node in enrichment.iter_concept_nodes(project_root):
        assert "broader" not in node
        assert "related_devatas" not in node


def test_concept_node_values_are_neo4j_storable(project_root: pathlib.Path) -> None:
    for node in enrichment.iter_concept_nodes(project_root):
        for key, value in node.items():
            assert isinstance(value, str | int | float | bool | list), key
            if isinstance(value, list):
                assert all(isinstance(item, str) for item in value), key


def test_alias_rows_flatten_both_languages_and_mark_the_preferred_form(
    project_root: pathlib.Path,
) -> None:
    rows = list(enrichment.iter_concept_alias_rows(project_root))
    fire = [r for r in rows if r["concept_id"] == "VG:CONCEPT:FIRE"]
    assert [(r["alias"], r["language"]) for r in fire] == [
        ("agni", "sa"),
        ("agní", "sa"),
        ("fire", "en"),
        ("flame", "en"),
    ]
    assert [r["alias"] for r in fire if r["is_preferred"]] == ["agni", "fire"]


def test_concept_hierarchy_makes_the_broader_concept_the_subject(
    project_root: pathlib.Path,
) -> None:
    rels = list(enrichment.iter_concept_hierarchy_rels(project_root))
    assert len(rels) == 1
    rel = rels[0]
    assert rel["predicate"] == "BROADER_THAN"
    assert rel["subject_key"] == "VG:CONCEPT:FIRE"
    assert rel["object_key"] == "VG:CONCEPT:RITUAL_FIRE"


def test_lexicon_edges_carry_a_synthesised_provenance_envelope(
    project_root: pathlib.Path,
) -> None:
    rel = next(iter(enrichment.iter_concept_hierarchy_rels(project_root)))
    assert rel["trust"] == "SOURCE_EXPLICIT"
    assert rel["method"] == enrichment.LEXICON_HIERARCHY_METHOD
    assert rel["evidence_count"] == 1
    spans = json.loads(rel["evidence"])
    # The locator is the lexicon row that states the claim -- the narrower concept, whose
    # "broader" field named the other one -- not the edge's subject.
    assert spans[0]["locator"] == "VG:CONCEPT:RITUAL_FIRE"
    assert spans[0]["surface"] == enrichment.LEXICON_SURFACE
    assert rel["pipeline_version"] == PIPELINE_VERSION


def test_devata_concept_rels_use_the_registry_entity_key(project_root: pathlib.Path) -> None:
    rels = list(enrichment.iter_devata_concept_rels(project_root))
    assert len(rels) == 1
    assert rels[0]["predicate"] == "DEVATA_ASSOCIATED_WITH"
    assert rels[0]["subject_key"] == "VG:DEVATA:AGNIH"
    assert rels[0]["object_key"] == "VG:CONCEPT:FIRE"


def test_formula_nodes_json_encode_the_map_and_keep_the_list(
    project_root: pathlib.Path,
) -> None:
    node = next(iter(enrichment.iter_formula_nodes(project_root)))
    assert node["vedas"] == ["RV", "SV"]
    assert json.loads(node["veda_counts"]) == {"RV": 4, "SV": 3}
    assert node["cross_veda"] is True
    assert node["mantra_count"] == 5
    assert node["evidence_count"] == 2


def test_formula_occurrence_rels_point_passage_at_formula(project_root: pathlib.Path) -> None:
    rels = list(enrichment.iter_formula_occurrence_rels(project_root))
    assert len(rels) == 3
    assert {r["predicate"] for r in rels} == {"USES_FORMULA"}
    assert rels[0]["subject_key"] == "VG:RV:1.1.1"
    assert rels[0]["object_key"] == "VG:ENRICH:FORMULA:aaaa"


def test_parallel_rels_carry_predicate_and_full_metrics(project_root: pathlib.Path) -> None:
    rels = list(enrichment.iter_cross_veda_parallel_rels(project_root))
    assert [r["predicate"] for r in rels] == ["EXACT_PARALLEL_OF", "NEAR_PARALLEL_OF"]
    exact = rels[0]
    assert exact["veda_pair"] == "RV-SV"
    assert exact["match_level"] == "ACCENT_INSENSITIVE"
    assert exact["levels_reached"] == [
        "ACCENT_INSENSITIVE",
        "SCRIPT_FOLDED",
        "SANDHI_INSENSITIVE",
    ]
    assert exact["similarity"] == 1.0
    assert exact["edit_ratio"] == 1.0


def test_evidence_is_a_json_string_whichever_shape_the_row_used(
    project_root: pathlib.Path,
) -> None:
    rels = list(enrichment.iter_cross_veda_parallel_rels(project_root))
    from_list, from_string = rels[0], rels[1]
    assert isinstance(from_list["evidence"], str)
    assert json.loads(from_list["evidence"])[0]["quote"] == "agnim ile"
    assert from_list["evidence_count"] == 2
    assert isinstance(from_string["evidence"], str)
    assert json.loads(from_string["evidence"])[0]["locator"] == "VG:RV:1.2.3"
    assert from_string["evidence_count"] == 1


def test_relationship_rows_are_neo4j_storable_scalars(project_root: pathlib.Path) -> None:
    readers = (
        enrichment.iter_concept_hierarchy_rels,
        enrichment.iter_devata_concept_rels,
        enrichment.iter_formula_occurrence_rels,
        enrichment.iter_cross_veda_parallel_rels,
        enrichment.iter_concept_assertion_rels,
        enrichment.iter_semantic_candidate_rels,
    )
    for reader in readers:
        for row in reader(project_root):
            for key, value in row.items():
                assert isinstance(value, str | int | float | bool | list), (reader, key)
                if isinstance(value, list):
                    assert all(isinstance(item, str) for item in value), (reader, key)


def test_concept_assertion_rels_are_about_concept(project_root: pathlib.Path) -> None:
    rel = next(iter(enrichment.iter_concept_assertion_rels(project_root)))
    assert rel["predicate"] == "ABOUT_CONCEPT"
    assert rel["subject_key"] == "VG:RV:1.1.1"
    assert rel["object_key"] == "VG:CONCEPT:FIRE"
    assert rel["confidence"] == 0.88


def test_semantic_candidate_rels_keep_predicate_and_object_kind(
    project_root: pathlib.Path,
) -> None:
    rels = list(enrichment.iter_semantic_candidate_rels(project_root))
    assert [(r["predicate"], r["object_kind"]) for r in rels] == [
        ("PRAISES", "COSMIC_ENTITY"),
        ("INVOKES", "DEVATA"),
    ]
    assert all(r["state"] == "CANDIDATE" for r in rels)
    assert all(r["trust"] == "LLM_EXTRACTED" for r in rels)


def test_manifest_round_trips(project_root: pathlib.Path) -> None:
    assert enrichment.read_manifest(project_root)["run_id"] == _RUN_ID


# ---------------------------------------------------------------------------
# Missing artifacts
# ---------------------------------------------------------------------------


def test_every_reader_yields_nothing_when_the_artifacts_are_absent(
    tmp_path: pathlib.Path,
) -> None:
    readers = (
        enrichment.iter_concept_nodes,
        enrichment.iter_concept_alias_rows,
        enrichment.iter_concept_hierarchy_rels,
        enrichment.iter_devata_concept_rels,
        enrichment.iter_formula_nodes,
        enrichment.iter_formula_occurrence_rels,
        enrichment.iter_cross_veda_parallel_rels,
        enrichment.iter_concept_assertion_rels,
        enrichment.iter_semantic_candidate_rels,
    )
    for reader in readers:
        assert list(reader(tmp_path)) == [], reader.__name__
    assert enrichment.read_manifest(tmp_path) == {}


def test_load_enrichment_against_an_empty_directory_is_a_clean_no_op(
    tmp_path: pathlib.Path,
) -> None:
    session = FakeSession()
    counts = enrichment_loader.load_enrichment(session, tmp_path)
    assert counts["Concept"] == 0
    assert counts["Formula"] == 0
    assert counts["unmatched_total"] == 0
    assert counts["duplicate_rows_total"] == 0
    # The schema still gets applied; nothing else runs.
    assert all("UNWIND" not in c for c in session.cypher)


def test_blank_lines_in_an_artifact_are_skipped(tmp_path: pathlib.Path) -> None:
    path = enrichment.enrichment_dir(tmp_path) / enrichment.CONCEPTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n" + json.dumps(CONCEPT_ROWS[0], ensure_ascii=False) + "\n\n\n", encoding="utf-8"
    )
    assert len(list(enrichment.iter_concept_nodes(tmp_path))) == 1


# ---------------------------------------------------------------------------
# Predicate injection
# ---------------------------------------------------------------------------


def _write_parallel_with_predicate(root: pathlib.Path, predicate: str) -> None:
    row = dict(PARALLEL_ROWS[0])
    row["predicate"] = predicate
    _write_jsonl(enrichment.enrichment_dir(root) / enrichment.PARALLELS_FILE, [row])


@pytest.mark.parametrize(
    "predicate",
    [
        "CAUSES",  # refused by name in the frozen ontology
        "IDENTIFIES_WITH",  # refused: the REPRESENTS claim under another name
        "TOTALLY_MADE_UP",
        "EXACT_PARALLEL_OF]->(x) DETACH DELETE x //",  # a Cypher injection attempt
        "",
    ],
)
def test_an_uncontrolled_predicate_is_rejected_and_never_reaches_cypher(
    tmp_path: pathlib.Path, predicate: str
) -> None:
    _write_parallel_with_predicate(tmp_path, predicate)
    session = FakeSession()
    with pytest.raises(UncontrolledPredicateError):
        enrichment_loader.merge_cross_veda_parallel_rels(session, tmp_path)
    assert session.calls == []
    assert all(predicate not in c for c in session.cypher if predicate)


def test_a_controlled_predicate_in_the_wrong_artifact_is_rejected(
    tmp_path: pathlib.Path,
) -> None:
    """ABOUT_CONCEPT is controlled, but a parallels file has no query for it.

    Rejecting this matters as much as rejecting an invented name: loading it against the
    parallel query would MATCH a Passage where a Concept belongs and quietly produce zero
    edges, which is indistinguishable from "there were none".
    """
    _write_parallel_with_predicate(tmp_path, "ABOUT_CONCEPT")
    session = FakeSession()
    with pytest.raises(UncontrolledPredicateError, match="no loader query"):
        enrichment_loader.merge_cross_veda_parallel_rels(session, tmp_path)
    assert session.calls == []


def test_an_unknown_semantic_object_kind_is_rejected(tmp_path: pathlib.Path) -> None:
    row = dict(SEMANTIC_ROWS[0])
    row["object_kind"] = "Lemma"
    _write_jsonl(
        enrichment.enrichment_dir(tmp_path) / enrichment.SEMANTIC_CANDIDATES_FILE, [row]
    )
    session = FakeSession()
    with pytest.raises(UnknownObjectKindError):
        enrichment_loader.merge_semantic_candidate_rels(session, tmp_path)
    assert session.calls == []


def test_every_generated_query_names_only_a_controlled_predicate() -> None:
    tables = (
        enrichment_loader._PARALLEL_QUERIES,
        enrichment_loader._USES_FORMULA_QUERIES,
        enrichment_loader._BROADER_QUERIES,
        enrichment_loader._DEVATA_CONCEPT_QUERIES,
        enrichment_loader._ABOUT_CONCEPT_QUERIES,
    )
    for table in tables:
        for key in table:
            assert key in CONTROLLED_PREDICATES, key
    for key in enrichment_loader._SEMANTIC_QUERIES:
        predicate, _, label = key.partition("|")
        assert predicate in CONTROLLED_PREDICATES, key
        assert label in {"Concept", "Devata"}, key


def test_relationship_type_validation_refuses_anything_outside_the_vocabulary() -> None:
    with pytest.raises(UncontrolledPredicateError):
        enrichment_loader._relationship_type("CAUSES")
    with pytest.raises(UncontrolledPredicateError):
        enrichment_loader._relationship_type("EXACT_PARALLEL_OF]->() DELETE x")
    assert enrichment_loader._relationship_type("EXACT_PARALLEL_OF") == "EXACT_PARALLEL_OF"


# ---------------------------------------------------------------------------
# Loader behaviour
# ---------------------------------------------------------------------------


def _all_queries() -> list[str]:
    return [
        *enrichment_loader._PARALLEL_QUERIES.values(),
        *enrichment_loader._USES_FORMULA_QUERIES.values(),
        *enrichment_loader._BROADER_QUERIES.values(),
        *enrichment_loader._DEVATA_CONCEPT_QUERIES.values(),
        *enrichment_loader._ABOUT_CONCEPT_QUERIES.values(),
        *enrichment_loader._SEMANTIC_QUERIES.values(),
    ]


def test_every_relationship_query_sets_the_whole_provenance_envelope() -> None:
    required = [
        "r.trust",
        "r.method",
        "r.score",
        "r.evidence",
        "r.evidence_count",
        "r.state",
        "r.pipeline_version",
        "r.run_id",
        "r.model",
        "r.prompt_policy",
    ]
    for query in _all_queries():
        for prop in required:
            assert f"{prop} = row." in query, (prop, query)


def test_every_relationship_query_pins_pipeline_version_inside_the_merge_pattern() -> None:
    """The property in the MERGE pattern is what stops this layer clobbering the other.

    A bare ``MERGE (a)-[r:EXACT_PARALLEL_OF]->(b)`` would match the within-Rigveda lexical
    edge that already exists between two RV passages and then SET the enrichment envelope
    over its methods, strongest_method and status.
    """
    for query in _all_queries():
        assert "{pipeline_version: row.pipeline_version}]->(b)" in query, query


def test_every_relationship_query_matches_endpoints_and_returns_a_merge_count() -> None:
    for query in _all_queries():
        assert query.count("MATCH ") == 2, query
        assert "MERGE (a)-[r:" in query, query
        assert "RETURN count(DISTINCT r) AS merged" in query, query


def test_counts_are_distinct_edges_not_rows_read(project_root: pathlib.Path) -> None:
    """Three occurrence rows, two distinct pairs, so the report must say two.

    Counting rows would report three USES_FORMULA edges against two in the database, and
    the missing one reads as a silently dropped edge rather than as a duplicate row.
    """
    session = FakeSession()
    result = enrichment_loader.merge_formula_occurrence_rels(session, project_root)
    assert result.merged["USES_FORMULA"] == 2
    assert result.duplicate_rows["USES_FORMULA"] == 1
    assert result.unmatched["USES_FORMULA"] == 0
    assert len(session.rows_for("USES_FORMULA")) == 2


def test_counts_come_from_the_database_not_from_the_batch_size(
    project_root: pathlib.Path,
) -> None:
    """A row whose endpoints are missing is unmatched, and unmatched is reported."""

    def merged_for(_cypher: str, rows: list[dict[str, Any]]) -> int:
        return max(len(rows) - 1, 0)

    session = FakeSession(merged_for=merged_for)
    result = enrichment_loader.merge_cross_veda_parallel_rels(session, project_root)
    assert result.merged == {"EXACT_PARALLEL_OF": 0, "NEAR_PARALLEL_OF": 0}
    assert result.unmatched == {"EXACT_PARALLEL_OF": 1, "NEAR_PARALLEL_OF": 1}
    assert result.total_unmatched == 2


def test_each_predicate_runs_against_its_own_query(project_root: pathlib.Path) -> None:
    session = FakeSession()
    enrichment_loader.merge_cross_veda_parallel_rels(session, project_root)
    types = [c.split("MERGE (a)-[r:")[1].split(" ")[0] for c in session.cypher]
    assert sorted(types) == ["EXACT_PARALLEL_OF", "NEAR_PARALLEL_OF"]


def test_semantic_candidates_route_on_the_resolved_object_label(
    project_root: pathlib.Path,
) -> None:
    session = FakeSession()
    result = enrichment_loader.merge_semantic_candidate_rels(session, project_root)
    assert result.merged == {"PRAISES|Concept": 1, "INVOKES|Devata": 1}
    joined = "\n".join(session.cypher)
    assert "(b:Concept {concept_id: row.object_key})" in joined
    assert "(b:Devata {entity_key: row.object_key})" in joined


def test_node_merges_deduplicate_on_the_identity_field(tmp_path: pathlib.Path) -> None:
    _write_jsonl(
        enrichment.enrichment_dir(tmp_path) / enrichment.CONCEPTS_FILE,
        [CONCEPT_ROWS[0], CONCEPT_ROWS[1], CONCEPT_ROWS[0]],
    )
    session = FakeSession()
    distinct, duplicates = enrichment_loader.merge_concept_nodes(session, tmp_path)
    assert (distinct, duplicates) == (2, 1)
    assert len(session.rows_for("MERGE (c:Concept")) == 2


def test_load_enrichment_reports_counts_and_unmatched_rows(
    project_root: pathlib.Path,
) -> None:
    def merged_for(cypher: str, rows: list[dict[str, Any]]) -> int:
        # Pretend the Devata registry node is absent, so that edge finds no endpoint.
        return 0 if "DEVATA_ASSOCIATED_WITH" in cypher else len(rows)

    session = FakeSession(merged_for=merged_for)
    counts = enrichment_loader.load_enrichment(session, project_root)

    assert counts["Concept"] == 2
    assert counts["Formula"] == 1
    assert counts["BROADER_THAN"] == 1
    assert counts["USES_FORMULA"] == 2
    assert counts["EXACT_PARALLEL_OF"] == 1
    assert counts["NEAR_PARALLEL_OF"] == 1
    assert counts["ABOUT_CONCEPT"] == 1
    assert counts["PRAISES"] == 1
    assert counts["INVOKES"] == 1

    assert counts["DEVATA_ASSOCIATED_WITH"] == 0
    assert counts["unmatched_DEVATA_ASSOCIATED_WITH"] == 1
    assert counts["unmatched_total"] == 1
    assert counts["duplicate_rows_total"] == 1
    assert all(isinstance(v, int) for v in counts.values())


def test_load_enrichment_applies_the_schema_before_merging(
    project_root: pathlib.Path,
) -> None:
    session = FakeSession()
    enrichment_loader.load_enrichment(session, project_root)
    first_merge = next(i for i, c in enumerate(session.cypher) if "UNWIND" in c)
    schema_statements = set(enrichment_schema.all_enrichment_schema_cypher())
    assert schema_statements.issubset(set(session.cypher[:first_merge]))


def test_merged_count_tolerates_an_empty_result() -> None:
    assert enrichment_loader._merged_count([]) == 0
    assert enrichment_loader._merged_count([{"merged": None}]) == 0
    assert enrichment_loader._merged_count([{"merged": 3}, {"merged": 4}]) == 7


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_every_schema_statement_is_idempotent() -> None:
    for statement in enrichment_schema.all_enrichment_schema_cypher():
        assert "IF NOT EXISTS" in statement, statement


def test_schema_statements_are_well_formed_cypher() -> None:
    for statement in enrichment_schema.enrichment_constraints():
        assert statement.startswith("CREATE CONSTRAINT ")
        assert " REQUIRE " in statement
        assert " IS UNIQUE" in statement
    for statement in enrichment_schema.enrichment_indexes():
        assert statement.startswith(("CREATE INDEX ", "CREATE FULLTEXT INDEX "))
        assert " FOR " in statement
        assert " ON " in statement


def test_schema_names_are_unique_and_namespaced() -> None:
    names = [
        statement.split(" IF NOT EXISTS")[0].split()[-1]
        for statement in enrichment_schema.all_enrichment_schema_cypher()
    ]
    assert len(names) == len(set(names))
    assert all(name.startswith("enrichment_") for name in names)


def test_schema_constraints_are_applied_before_indexes() -> None:
    statements = enrichment_schema.all_enrichment_schema_cypher()
    constraints = enrichment_schema.enrichment_constraints()
    assert statements[: len(constraints)] == constraints
    assert len(statements) == len(constraints) + len(enrichment_schema.enrichment_indexes())


def test_schema_accessors_return_copies() -> None:
    first = enrichment_schema.enrichment_indexes()
    first.append("CREATE INDEX bogus IF NOT EXISTS FOR (n:Nope) ON (n.x)")
    assert "CREATE INDEX bogus IF NOT EXISTS FOR (n:Nope) ON (n.x)" not in (
        enrichment_schema.enrichment_indexes()
    )


def test_relationship_indexes_cover_the_matrix_query_properties() -> None:
    statements = enrichment_schema.all_enrichment_schema_cypher()
    for rel_type in enrichment_schema.PARALLEL_REL_TYPES:
        for prop in ("veda_pair", "trust", "score", "pipeline_version"):
            needle = f"FOR ()-[r:{rel_type}]-() ON (r.{prop})"
            assert any(needle in statement for statement in statements), needle


def test_node_indexes_cover_the_deliverable_filters() -> None:
    statements = "\n".join(enrichment_schema.all_enrichment_schema_cypher())
    for needle in (
        "FOR (n:Formula) ON (n.cross_veda)",
        "FOR (n:Formula) ON (n.mantra_count)",
        "FOR (n:Concept) ON (n.node_type)",
        "FOR (n:Concept) ON (n.preferred_label_en)",
    ):
        assert needle in statements, needle


def test_uniqueness_constraints_exist_for_both_new_labels() -> None:
    joined = "\n".join(enrichment_schema.enrichment_constraints())
    assert "(n:Concept) REQUIRE n.concept_id IS UNIQUE" in joined
    assert "(n:Formula) REQUIRE n.formula_id IS UNIQUE" in joined


# ---------------------------------------------------------------------------
# Live database
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)
def test_schema_is_accepted_by_neo4j() -> None:
    """Apply the schema twice against a real server.

    Creating constraints and indexes is the only thing this touches; no node, relationship
    or property is written or removed. Applying it twice is the point -- the second pass is
    what proves ``IF NOT EXISTS`` means what the unit tests assume it means.
    """
    from neo4j import GraphDatabase

    uri = os.environ.get("VEDAGRAPH_NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("VEDAGRAPH_NEO4J_USER", "neo4j")
    password = os.environ.get("VEDAGRAPH_NEO4J_PASSWORD", "vedagraph_dev")
    statements = enrichment_schema.all_enrichment_schema_cypher()

    with GraphDatabase.driver(uri, auth=(user, password)) as driver, driver.session() as session:
        for _pass in range(2):
            for statement in statements:
                session.run(statement).consume()
        names = {
            record["name"]
            for record in session.run(
                "SHOW INDEXES YIELD name WHERE name STARTS WITH 'enrichment' RETURN name"
            )
        }
    assert len(names) >= len(enrichment_schema.enrichment_indexes())
