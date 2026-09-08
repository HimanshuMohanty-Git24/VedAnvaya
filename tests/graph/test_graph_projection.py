"""Tests for corpus projection: node/rel iterators and parent-key derivation."""

from __future__ import annotations

import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def test_iter_work_nodes_returns_four_works() -> None:
    from vedagraph.graph.projection import iter_work_nodes

    works = list(iter_work_nodes(PROJECT_ROOT))
    assert len(works) == 4
    work_ids = {w["work_id"] for w in works}
    assert "VG:WORK:RV:SAK" in work_ids
    assert "VG:WORK:SV:KAU" in work_ids
    assert "VG:WORK:YV:VSM" in work_ids
    assert "VG:WORK:AV:SAU" in work_ids


def test_iter_passage_nodes_rv_count() -> None:
    from vedagraph.graph.projection import iter_passage_nodes, manifest_passage_count

    rv_passages = [p for p in iter_passage_nodes(PROJECT_ROOT) if p["veda"] == "RV"]
    assert len(rv_passages) == manifest_passage_count("RV")


def test_iter_passage_nodes_sv_count() -> None:
    from vedagraph.graph.projection import iter_passage_nodes, manifest_passage_count

    sv_passages = [p for p in iter_passage_nodes(PROJECT_ROOT) if p["veda"] == "SV"]
    assert len(sv_passages) == manifest_passage_count("SV")


def test_iter_passage_nodes_yv_count() -> None:
    from vedagraph.graph.projection import iter_passage_nodes, manifest_passage_count

    yv_passages = [p for p in iter_passage_nodes(PROJECT_ROOT) if p["veda"] == "YV"]
    assert len(yv_passages) == manifest_passage_count("YV")


def test_iter_passage_nodes_av_count() -> None:
    from vedagraph.graph.projection import iter_passage_nodes, manifest_passage_count

    av_passages = [p for p in iter_passage_nodes(PROJECT_ROOT) if p["veda"] == "AV"]
    assert len(av_passages) == manifest_passage_count("AV")


def test_rv_mantra_has_parent_key() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    for p in iter_passage_nodes(PROJECT_ROOT):
        if p["veda"] == "RV" and p["entity_type"] == "MANTRA":
            assert p["parent_key"] is not None
            break


def test_all_passages_have_required_fields() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    required = {"canonical_key", "canonical_urn", "entity_id", "work_id", "veda"}
    for p in iter_passage_nodes(PROJECT_ROOT):
        for field in required:
            assert field in p, f"Missing field {field!r} in {p.get('canonical_key')}"


def test_no_duplicate_canonical_keys() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    keys = [p["canonical_key"] for p in iter_passage_nodes(PROJECT_ROOT)]
    assert len(keys) == len(set(keys)), "Duplicate canonical_keys found in projection"


def test_no_duplicate_entity_ids() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    ids = [p["entity_id"] for p in iter_passage_nodes(PROJECT_ROOT)]
    assert len(ids) == len(set(ids)), "Duplicate entity_ids found in projection"


def test_rv_111_is_present() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    keys = {p["canonical_key"] for p in iter_passage_nodes(PROJECT_ROOT)}
    assert "VG:RV:SAK:M01:S001:V001" in keys


def test_av_k20_is_present() -> None:
    from vedagraph.graph.projection import iter_passage_nodes

    keys = {p["canonical_key"] for p in iter_passage_nodes(PROJECT_ROOT)}
    assert "VG:AV:SAU:K20" in keys


def test_contains_rels_cover_all_passages() -> None:
    from vedagraph.graph.projection import iter_contains_rels, iter_passage_nodes

    passage_count = sum(1 for _ in iter_passage_nodes(PROJECT_ROOT))
    contains_count = sum(1 for _ in iter_contains_rels(PROJECT_ROOT))
    # Every passage should have exactly one CONTAINS incoming from parent or Work
    assert contains_count == passage_count


def test_sv_passage_derives_parent_key() -> None:
    """SV records carry no parent_key field; it must be derived from the key structure."""
    from vedagraph.graph.projection import iter_passage_nodes

    checked = 0
    for p in iter_passage_nodes(PROJECT_ROOT):
        if p["veda"] != "SV" or p["entity_type"] != "MANTRA":
            continue
        key = p["canonical_key"]
        assert p["parent_key"] is not None, f"SV mantra {key} has no derived parent"
        assert key.startswith(p["parent_key"] + ":"), (
            f"derived parent {p['parent_key']!r} is not a prefix of {key!r}"
        )
        checked += 1
    assert checked > 0, "no SV mantras found — projection or entity_type changed"


def test_top_level_passages_have_no_parent() -> None:
    """The four top-level structural nodes per Veda hang off the Work, not a Passage."""
    from vedagraph.graph.projection import iter_passage_nodes

    for p in iter_passage_nodes(PROJECT_ROOT):
        # A 4-segment key (e.g. VG:RV:SAK:M01) is a top-level node under the Work
        if len(p["canonical_key"].split(":")) == 4:
            assert p["parent_key"] is None, (
                f"{p['canonical_key']} is top-level but has parent {p['parent_key']!r}"
            )


def test_lemma_is_unique_but_normalized_lemma_is_not() -> None:
    """Lemma identity must be the accented citation form, not the normalized form.

    normalized_lemma collapses real lexical distinctions (atrá- / ā́tra / ā́tra- all
    normalize to "atra"). Constraining Lemma on it silently destroys ~246 lemmas, so
    the uniqueness constraint lives on `lemma` and normalized_lemma is a plain index.
    """
    from vedagraph.graph.lexical import iter_lemma_nodes

    lemmas = list(iter_lemma_nodes(PROJECT_ROOT))
    accented = [row["lemma"] for row in lemmas]
    normalized = [row["normalized_lemma"] for row in lemmas]

    assert len(accented) == len(set(accented)), "lemma is not unique — identity key is unsafe"
    assert len(set(normalized)) < len(set(accented)), (
        "normalized_lemma no longer collides; re-check whether it is now a safe identity key"
    )


def test_parallels_carry_two_distinct_predicates() -> None:
    """Near parallels must stay distinguishable from verbatim matches.

    mantra_parallels.jsonl mixes EXACT_PARALLEL_OF with PARALLEL_TO. Loading both
    under one relationship type would assert that a near parallel is an exact one.
    """
    from vedagraph.graph.lexical import iter_exact_parallel_rels

    rows = list(iter_exact_parallel_rels(PROJECT_ROOT))
    predicates = {row["predicate"] for row in rows}
    assert predicates == {"EXACT_PARALLEL_OF", "PARALLEL_TO"}, (
        f"unexpected parallel predicate set: {predicates}"
    )
    exact = [r for r in rows if r["predicate"] == "EXACT_PARALLEL_OF"]
    near = [r for r in rows if r["predicate"] == "PARALLEL_TO"]
    assert exact and near, "both parallel classes must be non-empty"
    assert all(r["status"] == "EXACT_PARALLEL" for r in exact)
    assert all(r["status"] == "HIGH_CONFIDENCE_NEAR_PARALLEL" for r in near)


def test_mentions_lemma_targets_resolvable_lemmas() -> None:
    """Every MENTIONS_LEMMA edge must point at a Lemma node that exists."""
    from vedagraph.graph.lexical import iter_lemma_nodes, iter_mentions_lemma_rels

    known = {row["lemma"] for row in iter_lemma_nodes(PROJECT_ROOT)}
    mentions = list(iter_mentions_lemma_rels(PROJECT_ROOT))
    assert mentions, "no MENTIONS_LEMMA edges produced"
    unresolved = {m["lemma"] for m in mentions if m["lemma"] not in known}
    assert not unresolved, f"{len(unresolved)} mention lemmas have no Lemma node"
    assert all(m["occurrence_count"] >= 1 for m in mentions)


def test_lemma_constraint_targets_the_unique_field() -> None:
    """Guard the schema against reverting Lemma identity to the colliding field."""
    from vedagraph.graph import schema

    lemma_constraints = [c for c in schema.CONSTRAINTS if ":Lemma)" in c]
    assert len(lemma_constraints) == 1
    assert "n.lemma IS UNIQUE" in lemma_constraints[0]
    assert "normalized_lemma" not in lemma_constraints[0]


@pytest.mark.parametrize("veda,expected_mantra_type", [
    ("RV", "MANTRA"),
    ("SV", "MANTRA"),
    ("YV", "MANTRA"),
    ("AV", "MANTRA"),
])
def test_leaf_passages_are_mantras(veda: str, expected_mantra_type: str) -> None:
    from vedagraph.graph.projection import iter_passage_nodes, manifest_mantra_count

    mantras = [
        p for p in iter_passage_nodes(PROJECT_ROOT)
        if p["veda"] == veda and p["entity_type"] == expected_mantra_type
    ]
    assert len(mantras) == manifest_mantra_count(veda)
