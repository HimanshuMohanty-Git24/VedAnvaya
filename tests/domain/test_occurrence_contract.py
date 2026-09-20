"""The occurrence-count contract, and the three ways it is allowed to fail.

GAP-QUALITY-006. ``occurrence_count`` was written by three loaders to three conventions:
the Yajurvedic one counted mantra-scope edges, the Atharvavedic one counted container-scope
edges, and the Rigvedic path wrote a literal ``0`` over the largest seer layer in the
corpus. ``:Devata`` and ``:Chandas`` were never written at all. Nothing recorded which
convention a figure was in, so no consumer could read the property correctly and
``src/vedagraph/api/ask/evidence.py`` printed it as "Registry occurrence count: 0".

Every test here is paired: a BAD input that must fail the gate and a GOOD input that must
pass it. A gate with only the GOOD half is the failure mode already recorded twice in
OWNER_DECISIONS.
"""

from __future__ import annotations

import pytest

from vedagraph.domain import occurrence_contract as contract


def _row(**overrides: object) -> dict[str, object]:
    row = {
        "entity_key": "VG:RISHI:RV:VASISTHA",
        "display_label": "Vasistha",
        "registry_namespace": "RV_WSC2023_ANUKRAMANI",
        "node_labels": ["Rishi"],
        "stored_occurrence_count": 0,
        "occurrence_count": 836,
        "occurrence_count_mantra_scope": 836,
        "occurrence_count_container_scope": 0,
        "occurrence_scope": contract.OCCURRENCE_SCOPE,
        "occurrence_predicate": "HAS_RISHI",
        "occurrence_contract_version": contract.CONTRACT_VERSION,
    }
    row.update(overrides)
    return row


def test_an_unrecognised_label_raises_rather_than_returning_none() -> None:
    """The property went missing on 789 nodes because nothing objected to its absence.

    ``:Formula`` genuinely carries an ``occurrence_count`` of its own, written by its own
    generator to its own meaning, and is deliberately outside this contract. Asking this
    contract for it must be an error and not a silent ``None``, or the next label added to
    the graph goes unwritten the same way.
    """
    assert contract.rule_for("Rishi").predicate == "HAS_RISHI"
    assert contract.rule_for("Devata").predicate == "HAS_DEVATA"
    assert contract.rule_for("Chandas").predicate == "HAS_CHANDAS"
    with pytest.raises(contract.UnknownOccurrenceLabel):
        contract.rule_for("Formula")
    with pytest.raises(contract.UnknownOccurrenceLabel):
        contract.rule_for("DevataAscription")


def test_the_devata_predicate_is_dedication_and_not_mention() -> None:
    """17,165 mentions against 10,558 dedications is two questions, not one number."""
    assert contract.rule_for("Devata").predicate == "HAS_DEVATA"
    assert "MENTIONS_DEVATA" not in contract.measure_cypher("Devata")


def test_the_grain_split_must_sum_to_the_headline() -> None:
    """BAD: a row whose scope note lies. GOOD: the same row, summing."""
    bad = _row(occurrence_count_mantra_scope=500, occurrence_count_container_scope=0)
    findings = contract.check_rows([bad])
    assert not findings["split_sums"]
    assert not findings["passes"]
    assert findings["split_mismatch_keys"] == ["VG:RISHI:RV:VASISTHA"]

    good = contract.check_rows([_row()])
    assert good["split_sums"]
    assert good["passes"]


def test_a_null_count_is_the_state_this_contract_ends() -> None:
    """BAD: the 214 :Devata and 575 :Chandas rows as they stand today."""
    bad = contract.check_rows([_row(occurrence_count=None)])
    assert not bad["every_node_covered"]
    assert not bad["passes"]
    assert contract.check_rows([_row()])["every_node_covered"]


def test_a_figure_without_its_scope_is_the_original_defect() -> None:
    """BAD: a count with no recorded scope is exactly what the three loaders produced."""
    bad = contract.check_rows([_row(occurrence_scope=None)])
    assert not bad["scope_recorded"]
    assert not bad["passes"]

    bad_predicate = contract.check_rows([_row(occurrence_predicate="")])
    assert not bad_predicate["scope_recorded"]

    assert contract.check_rows([_row()])["scope_recorded"]


def test_the_measure_cypher_is_label_scoped_at_both_grains() -> None:
    """An unlabelled MATCH made 39,461 bogus edges once; this one names its label.

    It must also split the grains, because the whole defect was that two loaders counted
    different grains and nothing said which.
    """
    cypher = contract.measure_cypher("Rishi")
    assert "MATCH (n:Rishi)" in cypher
    assert "(m:Mantra)-[e:HAS_RISHI]->(n)" in cypher
    assert "WHERE NOT p:Mantra" in cypher
    assert "MATCH (n)" not in cypher.replace("MATCH (n:Rishi)", "")


def test_the_written_property_set_is_the_whole_contract() -> None:
    """Landing half the set leaves a reader unable to tell which convention applies."""
    row = _row()
    for prop in contract.WRITTEN_PROPERTIES:
        assert prop in row, prop
    assert set(contract.WRITTEN_PROPERTIES) <= set(row)
