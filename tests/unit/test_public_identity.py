"""Publication identities must not alias their contextual passage."""
import pytest

from vedagraph.graph.public_identity import public_id, public_id_cypher
from vedagraph.api.services.graph_service import stable_id, node_view, _resolution_clause


def test_assertion_and_its_passage_are_distinct():
    passage = {"canonical_key": "VG:RV:SAK:M01:S001:V001"}
    assertion = {**passage, "assertion_key": passage["canonical_key"] + ":A001",
                 "display_type": "SEMANTIC_ASSERTION", "display_label": "Invokes"}
    assert public_id(assertion) == "semantic-assertion:VG:RV:SAK:M01:S001:V001:A001"
    assert public_id(assertion) != public_id(passage)
    assert node_view(assertion, ["SemanticAssertion"]).id == public_id(assertion)
    assert stable_id(assertion) == public_id(assertion)


@pytest.mark.parametrize("field", ["assertion_id", "entity_key", "canonical_key", "formula_id",
                                 "family_id", "group_id", "concept_id", "step_key"])
def test_existing_published_ids_are_preserved(field):
    assert public_id({field: "published:identifier"}) == "published:identifier"


def test_mutable_metadata_and_input_order_cannot_change_identity():
    original = {"assertion_key": "frozen:source:assertion", "canonical_key": "passage"}
    rebuilt = {"run_id": "different", "display_label": "changed", "assertion_ordinal": 999,
               "translation": "changed", **dict(reversed(list(original.items())))}
    assert public_id(original) == public_id(rebuilt)


def test_existing_assertion_id_takes_precedence_and_empty_values_do_not():
    assert public_id({"assertion_id": "legacy", "assertion_key": "key"}) == "legacy"
    assert public_id({"assertion_id": "", "assertion_key": "key"}) == "semantic-assertion:key"
    assert public_id({"assertion_id": "", "canonical_key": ""}) is None


def test_resolver_uses_bound_parameter_and_namespaced_key():
    clause = _resolution_clause("n", "node_id")
    assert "semantic-assertion:" in clause
    assert "n.assertion_key = substring(public_id, 19)" in clause
    assert "$node_id" in clause
    assert "elementId" not in public_id_cypher("n")
