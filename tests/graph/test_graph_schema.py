"""Tests for graph schema definitions."""

from __future__ import annotations

from vedagraph.graph import schema


def test_node_labels_are_strings() -> None:
    labels = [
        schema.LABEL_WORK,
        schema.LABEL_PASSAGE,
        schema.LABEL_MANTRA,
        schema.LABEL_TEXT_VERSION,
        schema.LABEL_TRANSLATION,
        schema.LABEL_SOURCE,
        schema.LABEL_RISHI,
        schema.LABEL_DEVATA,
        schema.LABEL_CHANDAS,
        schema.LABEL_LEMMA,
    ]
    for label in labels:
        assert isinstance(label, str)
        assert label


def test_relationship_types_are_strings() -> None:
    rels = [
        schema.REL_CONTAINS,
        schema.REL_HAS_TEXT_VERSION,
        schema.REL_HAS_TRANSLATION,
        schema.REL_HAS_RISHI,
        schema.REL_HAS_DEVATA,
        schema.REL_HAS_CHANDAS,
        schema.REL_MENTIONS_LEMMA,
        schema.REL_EXACT_PARALLEL_OF,
    ]
    for rel in rels:
        assert isinstance(rel, str)
        assert rel


def test_constraints_are_cypher_strings() -> None:
    for stmt in schema.CONSTRAINTS:
        assert isinstance(stmt, str)
        assert "CONSTRAINT" in stmt
        assert "REQUIRE" in stmt


def test_indexes_are_cypher_strings() -> None:
    for stmt in schema.INDEXES:
        assert isinstance(stmt, str)
        assert "INDEX" in stmt


def test_all_schema_cypher_includes_constraints_and_indexes() -> None:
    all_cypher = schema.all_schema_cypher()
    assert len(all_cypher) == len(schema.CONSTRAINTS) + len(schema.INDEXES)


def test_no_duplicate_constraint_names() -> None:
    names = [s.split()[2] for s in schema.CONSTRAINTS]
    assert len(names) == len(set(names)), "Duplicate constraint names found"
