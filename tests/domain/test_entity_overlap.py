"""Contract tests for the materialised cross-Veda entity-vocabulary-overlap layer.

Offline, on synthetic mention data, because every property worth pinning here is a
property of the computation rather than of the corpus: that it is cross-Veda only, that it
does not re-assert textual reuse, that a pair joined by rare vocabulary outranks a pair
joined by vocabulary every hymn uses, and that it stores each pair once in a canonical
direction so the arrow cannot be read as "a is the source of b".
"""

from __future__ import annotations

from typing import Any

from vedagraph.domain.entity_overlap import (
    MIN_SHARED,
    PIPELINE_VERSION,
    OverlapPair,
    compute_pairs,
    load,
)


def _mentions(*rows: tuple[str, str, tuple[str, ...]]) -> list[tuple[str, str, str]]:
    return [(passage, veda, entity) for passage, veda, entities in rows for entity in entities]


COMMON = ("agni", "soma", "yajna")
RARE = ("vedi", "sruc", "camasa")


def test_pairs_are_cross_veda_only() -> None:
    """A same-Veda pair is not an answer to "which cross-Veda passages resemble"."""
    mentions = _mentions(
        ("RV:1", "RV", COMMON),
        ("RV:2", "RV", COMMON),
        ("AV:1", "AV", COMMON),
    )
    pairs = compute_pairs(mentions, already_parallel=set())
    assert {(p.passage_a, p.passage_b) for p in pairs} == {
        ("AV:1", "RV:1"),
        ("AV:1", "RV:2"),
    }
    assert all(p.veda_a != p.veda_b for p in pairs)


def test_a_pair_below_the_threshold_is_not_recorded() -> None:
    """Two shared entities is not the question the frozen benchmark asks."""
    mentions = _mentions(
        ("RV:1", "RV", ("agni", "soma", "indra")),
        ("AV:1", "AV", ("agni", "soma", "rudra")),
    )
    assert compute_pairs(mentions, already_parallel=set()) == []
    assert MIN_SHARED == 3


def test_pairs_already_joined_by_textual_reuse_are_dropped() -> None:
    """Both questions ask for resemblance *without* shared text."""
    mentions = _mentions(("RV:1", "RV", COMMON), ("AV:1", "AV", COMMON))
    assert compute_pairs(mentions, already_parallel={("AV:1", "RV:1")}) == []
    assert len(compute_pairs(mentions, already_parallel=set())) == 1


def test_rare_shared_vocabulary_outranks_common_shared_vocabulary() -> None:
    """The defect this layer fixes: a hub-driven pair ranking beside a specific one.

    Both pairs share exactly three entities, so the old count-only ranking could not
    separate them. One shares vocabulary present in every passage; the other shares
    vocabulary present in two.
    """
    filler = [(f"RV:f{i}", "RV", COMMON) for i in range(12)]
    mentions = _mentions(
        *filler,
        ("RV:common", "RV", COMMON),
        ("AV:common", "AV", COMMON),
        ("RV:rare", "RV", RARE),
        ("AV:rare", "AV", RARE),
    )
    pairs = compute_pairs(mentions, already_parallel=set())
    by_key = {(p.passage_a, p.passage_b): p for p in pairs}
    rare = by_key[("AV:rare", "RV:rare")]
    common = by_key[("AV:common", "RV:common")]

    assert rare.shared_entities == common.shared_entities == 3
    assert rare.distinctiveness > common.distinctiveness
    assert rare.rarest_shared_df < common.rarest_shared_df
    # And the sort puts the well-evidenced pair first, so a caller taking the top N
    # gets the specific resemblances rather than the vocabulary-driven ones.
    assert pairs[0].rarest_shared_df <= pairs[-1].rarest_shared_df


def test_each_pair_is_stored_once_in_a_canonical_direction() -> None:
    """The arrow must not imply a source, because this layer cannot establish one."""
    mentions = _mentions(("YV:1", "YV", COMMON), ("AV:1", "AV", COMMON))
    pairs = compute_pairs(mentions, already_parallel=set())
    assert len(pairs) == 1
    assert pairs[0].passage_a < pairs[0].passage_b


def test_shared_entity_keys_are_recorded_so_a_pair_can_explain_itself() -> None:
    """A similarity edge that cannot say what is shared is not evidence-bearing."""
    mentions = _mentions(
        ("RV:1", "RV", ("agni", "soma", "yajna", "indra")),
        ("SV:1", "SV", ("agni", "soma", "yajna", "rudra")),
    )
    pair = compute_pairs(mentions, already_parallel=set())[0]
    assert pair.shared_entity_keys == ("agni", "soma", "yajna")
    assert pair.as_row()["shared_entities"] == 3
    assert pair.as_row()["shared_entity_keys"] == ["agni", "soma", "yajna"]


class _Result:
    def __init__(self, value: int) -> None:
        self._value = value

    def single(self) -> dict[str, int]:
        return {"c": self._value}

    def __iter__(self) -> Any:
        return iter(())


class _FakeSession:
    def __init__(self, count: int) -> None:
        self.statements: list[str] = []
        self._count = count

    def run(self, query: str, **parameters: Any) -> _Result:
        self.statements.append(query)
        return _Result(self._count)


def test_the_loader_retires_by_run_id_not_by_pipeline_version() -> None:
    """The regression this pins actually happened, and its own diff caught it.

    Retiring on ``pipeline_version`` removes edges written by older CODE but not edges
    written from older DATA under the same version. When the mention layer shrank by four
    edges, eight pairs stopped qualifying, were not rewritten, were not retired, and the
    loader reported ``sent=2141 landed=2149`` -- landed exceeding sent, which is the
    signature of a stale survivor. ``run_id`` is fresh per call, so anything not
    rewritten this run is stale by construction.
    """
    session = _FakeSession(count=1)
    pair = OverlapPair(
        passage_a="AV:1",
        passage_b="RV:1",
        veda_a="AV",
        veda_b="RV",
        shared_entity_keys=("agni", "soma", "yajna"),
        distinctiveness=3.0,
        rarest_shared_df=2,
    )
    report = load(session, [pair])
    assert report.sent == 1
    deletes = [s for s in session.statements if "DELETE r" in s]
    assert len(deletes) == 1
    assert "r.run_id" in deletes[0], "retirement must key on the run, not the version"
    assert "pipeline_version" not in deletes[0], (
        "retiring on pipeline_version leaves pairs that stopped qualifying under the "
        "same code version, which is the defect this test exists for"
    )
    assert "retired" in report.detail
    assert "run_id" in report.detail


def test_every_written_edge_carries_a_grade_and_says_what_it_does_not_claim() -> None:
    """The 100%-graded invariant must survive a new predicate, and so must honesty."""
    session = _FakeSession(count=1)
    load(
        session,
        [
            OverlapPair(
                passage_a="AV:1",
                passage_b="RV:1",
                veda_a="AV",
                veda_b="RV",
                shared_entity_keys=("agni", "soma", "yajna"),
                distinctiveness=3.0,
                rarest_shared_df=2,
            )
        ],
    )
    write = next(
        s for s in session.statements if "MERGE (a)-[r:SHARES_ENTITY_VOCABULARY_WITH]" in s
    )
    for required in (
        "r.quality_tier",
        "r.grade_basis",
        "r.attribution_precision",
        "r.evidence",
        "r.evidence_count",
    ):
        assert required in write, required
    assert "express the same idea" in write, "the edge must state what it does not claim"
    assert PIPELINE_VERSION.startswith("entity-vocabulary-overlap")
