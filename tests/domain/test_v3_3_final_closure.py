"""Regression guards for the three V3.3 benchmark closure surfaces."""

from __future__ import annotations

import os
import pathlib

import pytest

from vedagraph.domain.queries import QUERIES_BY_NAME, questions_served
from vedagraph.domain.registry import load_domain_entities, merge_registry

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


def _run_live_query(name: str) -> list[dict[str, object]]:
    from neo4j import GraphDatabase

    query = QUERIES_BY_NAME[name]
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        with driver.session() as session:
            return [dict(row) for row in session.run(query.cypher, **query.parameters)]
    finally:
        driver.close()


def test_q10_registers_every_metal_the_enumeration_verses_attest() -> None:
    """VSM 18.13 lists hiraṇya, ayas, śyāma, loha, sīsa, trapu. All six need a node.

    Registering trapu alone re-broke Q10 by its own argument: śyāma sits two words
    later in the same enumeration, and a roster that harvests one and drops the other
    is the silent class-membership gap the benchmark graded MISLEADING.
    """
    merge_registry(PROJECT_ROOT)
    entities = {entity.concept_id: entity for entity in load_domain_entities(PROJECT_ROOT)}
    metals = {key for key, entity in entities.items() if entity.node_type == "METAL"}

    assert {
        "VG:CONCEPT:HIRANYA-GOLD",
        "VG:CONCEPT:AYAS-METAL",
        "VG:CONCEPT:SYAMA-DARK-METAL",
        "VG:CONCEPT:LOHA-COPPER",
        "VG:CONCEPT:SISA-LEAD",
        "VG:CONCEPT:TRAPU-TIN",
    } <= metals

    assert set(entities["VG:CONCEPT:TRAPU-TIN"].aliases_sa) == {"trapu"}
    # The bare stem token-matches the verb form at RV 6.5.7 and sits inside aśyāma 22
    # times, so only the exact attested inflections are admitted -- the ayas policy.
    # Both enumeration witnesses are needed: VSM 18.13 writes it with anusvara, AVS
    # 11.3.7 without, and registering only the first left the AV cell reading as a zero.
    assert set(entities["VG:CONCEPT:SYAMA-DARK-METAL"].aliases_sa) == {"śyāmaṃ", "śyāmam"}


def test_q23_maps_to_capability_status_not_a_pair_table() -> None:
    assert questions_served()[23] == ["deity_community_capability"]

    query = QUERIES_BY_NAME["deity_community_capability"]
    assert "INSUFFICIENT_EVIDENCE" in query.cypher
    assert "pairwise_edges" in query.cypher
    # Was `structure, 'UNSPECIFIED') <> 'HUMAN'`, which published eligible_deities: 192 --
    # 22 human patrons removed and the 7 danastuti labels and 28 NOT_DEITY abstractions
    # left in. GAP-ENTITY_COVERAGE-008 replaced it with the one documented predicate, which
    # reads 157. The old spelling is asserted ABSENT so it cannot come back.
    assert "d.is_deity" in query.cypher
    assert "devatas_without_an_eligibility_ruling" in query.cypher, (
        "the transitional state must be typed in the row: while the ruling layer has not "
        "landed, eligible_deities falls back to curated structure and a reader has no "
        "other way to know which figure they are holding"
    )
    assert "structure, 'UNSPECIFIED') <> 'HUMAN'" not in query.cypher
    assert "not a claim that Vedic deity communities do not exist" in query.caveat


def test_neighboring_deity_pair_queries_exclude_human_addressees() -> None:
    for name in (
        "deity_co_occurrence",
        "deity_pairs_far_above_chance",
        "deity_pairs_not_rigvedic",
    ):
        cypher = QUERIES_BY_NAME[name].cypher
        # Both endpoints gated on the recorded ruling. This required the structure list
        # "'HUMAN', 'PATRON_PRAISE'" in the text, which was the transitional shim's
        # fallback: correct while is_deity was landing, and a second eligibility predicate
        # once it had landed on all 214. The danastuti exclusion the old predicate missed
        # -- 50 dedications across 15 hymns, 9 partners -- is now carried by the ruling
        # itself (7 rows are non_deity_kind DANASTUTI_GIFT_PRAISE), which also excludes the
        # 28 abstractions the structure fallback admitted.
        assert "a.is_deity = true" in cypher, name
        assert "b.is_deity = true" in cypher, name
        assert "NOT coalesce(a.structure" not in cypher, name
        assert "coalesce(a.structure, 'UNSPECIFIED') <> 'HUMAN'" not in cypher, name


def test_q25_uses_curated_ritual_usage_instead_of_the_flat_object_class() -> None:
    assert questions_served()[25] == ["ritual_objects_recurring"]

    query = QUERIES_BY_NAME["ritual_objects_recurring"]
    assert "(r:Ritual)-[:USES_OBJECT]->(o:Object)" in query.cypher
    assert "o.display_type AS registry_type" in query.cypher
    assert "matched_mantras_minimum" in query.cypher
    assert "PARTIAL_ALIAS_RECALL" in query.cypher
    assert "chariots and thunderbolts" in query.caveat


@pytest.mark.live
@_LIVE
def test_live_q10_returns_a_complete_metal_by_veda_grid() -> None:
    """A cell that found nothing must say so in its own row.

    The V3.2 grading turned on silent omission: a reader ran the query, saw no tin,
    and concluded the Samhitas name five metals. A metal x Veda grid cannot omit a
    cell, so absence is always readable as a matcher fact and never as a corpus fact.
    """
    rows = _run_live_query("metals_by_veda")
    metals = {str(row["metal"]) for row in rows}
    vedas = {str(row["veda"]) for row in rows}
    assert vedas == {"RV", "SV", "YV", "AV"}
    assert len(rows) == len(metals) * 4
    assert {row["evidence_status"] for row in rows} == {
        "LEXICAL_MATCH_MINIMUM",
        "NO_LEXICAL_MATCH",
    }
    for row in rows:
        assert (row["mantras"] == 0) == (row["evidence_status"] == "NO_LEXICAL_MATCH")


@pytest.mark.live
@_LIVE
def test_live_q10_names_both_metal_enumeration_witnesses() -> None:
    """trapu and syama are named in both enumeration verses, so both Vedas must show."""
    rows = _run_live_query("metals_by_veda")
    matched = {
        (str(row["metal"]), str(row["veda"]))
        for row in rows
        if row["evidence_status"] == "LEXICAL_MATCH_MINIMUM"
    }
    assert ("tin (trapu)", "AV") in matched
    assert ("tin (trapu)", "YV") in matched
    assert ("dark metal (śyāma)", "YV") in matched
    # AVS 11.3.7, one verse before the trapu witness. Registering trapu without this
    # left the AV cell reading as a zero.
    assert ("dark metal (śyāma)", "AV") in matched


@pytest.mark.live
@_LIVE
def test_live_q10_syama_alias_did_not_land_on_the_verb_form() -> None:
    """The homonym guard, measured rather than asserted: two mantras, both enumerations.

    The bare stem would have taken RV 6.5.7 (a verb) and 22 hosts inside asyama.
    """
    rows = _run_live_query("metals_by_veda")
    syama = {str(r["veda"]): r["mantras"] for r in rows if r["metal"] == "dark metal (śyāma)"}
    assert syama == {"YV": 1, "AV": 1, "RV": 0, "SV": 0}


@pytest.mark.live
@_LIVE
def test_live_q10_normalises_per_veda_counts_for_corpus_size() -> None:
    """The criterion asks for normalisation, and it is not cosmetic: gold's raw
    ordering (RV 38 > AV 34) inverts once corpus size is divided out."""
    rows = _run_live_query("metals_by_veda")
    gold = {str(r["veda"]): r for r in rows if r["metal"] == "gold (hiraṇya)"}
    assert gold["RV"]["mantras"] > gold["AV"]["mantras"]
    assert gold["AV"]["per_1000_mantras"] > gold["RV"]["per_1000_mantras"]
    for row in rows:
        assert row["corpus_mantras"] > 0


@pytest.mark.live
@_LIVE
def test_live_q23_reports_insufficient_community_evidence() -> None:
    """Q23's capability row, with the eligibility disclosure it gained pinned too.

    This asserted a five-key dict by equality and broke when GAP-ENTITY_COVERAGE-008 added
    ``devatas_without_an_eligibility_ruling`` and ``devata_nodes`` to the row. Nothing it
    cared about had changed -- status, ``assigned_deities``, ``eligible_deities`` and
    ``evidence_scope`` were all still right -- so the failure was the test refusing a
    *widening*, and while it failed it was checking nothing at all.

    Rewritten to pin the widened shape rather than tolerate it, and the two new columns are
    now the more interesting assertions. The query's own caveat says
    ``devatas_without_an_eligibility_ruling`` "is the figure to read first: while it is 214
    the ruling layer has not landed and ``eligible_deities`` falls back to curated structure
    and reads 185; when it is 0 the ruling is in force and the figure is 157". Both figures
    were typed into prose and checked by nothing. They are checked here.

    The key set is asserted exactly, so the next column added to this row lands in front of
    someone instead of being absorbed -- which is the failure mode that produced this fix.
    """
    rows = _run_live_query("deity_community_capability")
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {
        "status",
        "assigned_deities",
        "eligible_deities",
        "devatas_without_an_eligibility_ruling",
        "devata_nodes",
        "pairwise_edges",
        "evidence_scope",
    }
    assert row["status"] == "INSUFFICIENT_EVIDENCE"
    assert row["evidence_scope"] == "PAIRWISE_CO_OCCURRENCE_IS_NOT_A_COMMUNITY_PARTITION"
    # No community partition is stored or computed, which is what the status means. A
    # non-zero here with this status would make the row contradict itself.
    assert int(row["assigned_deities"]) == 0
    # GAP-ENTITY_COVERAGE-008: an unruled node fails closed and silently shrinks the
    # pantheon, so this is the figure that must be 0 and the one the caveat says to read
    # first.
    assert int(row["devatas_without_an_eligibility_ruling"]) == 0
    assert int(row["devata_nodes"]) == 214
    # 157 is the ruling-in-force figure the caveat states. Pinned so the prose and the row
    # cannot drift apart; 185 is the fallback and would mean the ruling layer had come
    # undone.
    assert int(row["eligible_deities"]) == 157
    assert int(row["eligible_deities"]) < int(row["devata_nodes"])
    assert int(row["pairwise_edges"]) > 0


@pytest.mark.live
@_LIVE
def test_live_q33_pair_neighbor_remains_nonempty_and_excludes_humans() -> None:
    rows = _run_live_query("deity_co_occurrence")
    assert rows
    returned = {str(row[side]) for row in rows for side in ("deity_a", "deity_b")}
    assert "Rathaviti Darbhya" not in returned
    assert "Vasukra" not in returned


@pytest.mark.live
@_LIVE
def test_live_q25_returns_only_curated_implements_with_minimum_status() -> None:
    rows = _run_live_query("ritual_objects_recurring")
    assert rows
    returned = {str(row["ritual_implement"]) for row in rows}
    assert "chariot (ratha)" not in returned
    assert "thunderbolt (vajra)" not in returned
    assert {str(row["evidence_status"]) for row in rows} == {"PARTIAL_ALIAS_RECALL"}
    assert all(int(row["matched_mantras_minimum"]) > 0 for row in rows)
