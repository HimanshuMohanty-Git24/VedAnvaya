from uuid import uuid4

from vedagraph.models import SourceAssertion
from vedagraph.models.enums import AssertionStatus
from vedagraph.reconcile import ReconciliationPolicy


def assertion(source_id: str, value: int) -> SourceAssertion:
    return SourceAssertion(
        assertion_id=uuid4(),
        subject_id="VG:WORK:AV:SAU",
        predicate="REPORTED_UNIT_COUNT",
        value=value,
        source_id=source_id,
        source_locator="fixture",
    )


def test_conflicting_counts_are_retained_and_flagged() -> None:
    claims = [assertion("A", 5977), assertion("B", 5987)]
    winner = ReconciliationPolicy("counts", require_review_on_conflict=True).choose(claims)
    assert winner is None
    assert all(claim.status == AssertionStatus.CONFLICT for claim in claims)


def test_field_policy_selects_preferred_source_when_values_agree() -> None:
    claims = [assertion("LOW", 9), assertion("HIGH", 9)]
    winner = ReconciliationPolicy("structure", ("HIGH", "LOW")).choose(claims)
    assert winner is not None
    assert winner.source_id == "HIGH"
    assert len(claims) == 2
