"""Tests for query module (unit-level; no live Neo4j required)."""

from __future__ import annotations

from vedagraph.graph import queries


def test_all_query_functions_are_callable() -> None:
    fns = [
        queries.fetch_passage,
        queries.fetch_sukta_mantras,
        queries.fetch_passages_by_devata,
        queries.fetch_passages_by_rishi,
        queries.fetch_passages_by_chandas,
        queries.fetch_passage_with_translation,
        queries.fetch_exact_parallels,
        queries.fetch_sv_passages_related_to_rv,
        queries.fetch_yv_adhyaya,
        queries.fetch_av_kanda,
        queries.fetch_lemma_mentions,
        queries.graph_statistics,
        queries.orphan_passages,
        queries.duplicate_canonical_keys,
    ]
    for fn in fns:
        assert callable(fn)


def test_query_module_has_no_import_errors() -> None:
    import importlib

    mod = importlib.import_module("vedagraph.graph.queries")
    assert mod is not None
