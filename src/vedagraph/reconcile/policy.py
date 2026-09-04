"""Field-specific reconciliation policies."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from vedagraph.models import SourceAssertion
from vedagraph.models.enums import AssertionStatus


@dataclass(frozen=True)
class ReconciliationPolicy:
    policy_id: str
    source_preference: tuple[str, ...] = field(default_factory=tuple)
    require_review_on_conflict: bool = True

    def choose(self, assertions: list[SourceAssertion]) -> SourceAssertion | None:
        if not assertions:
            return None
        distinct_values = {repr(assertion.value) for assertion in assertions}
        if len(distinct_values) > 1 and self.require_review_on_conflict:
            for assertion in assertions:
                assertion.status = AssertionStatus.CONFLICT
            return None
        rank = {source_id: index for index, source_id in enumerate(self.source_preference)}
        winner = min(
            assertions,
            key=lambda item: (rank.get(item.source_id, len(rank)), str(item.assertion_id)),
        )
        for assertion in assertions:
            assertion.status = (
                AssertionStatus.ACCEPTED
                if assertion.assertion_id == winner.assertion_id
                else AssertionStatus.REJECTED
            )
        return winner


DEFAULT_POLICIES: dict[str, ReconciliationPolicy] = {
    "structure": ReconciliationPolicy("structure-v1", ("VHP", "GRETIL")),
    "sanskrit_text": ReconciliationPolicy("sanskrit-text-v1", ("GRETIL", "VHP")),
    "traditional_metadata": ReconciliationPolicy("traditional-metadata-v1", ("VHP",)),
    "translations": ReconciliationPolicy("translations-v1", ()),
    "audio": ReconciliationPolicy("audio-v1", ("VHP",)),
    "counts": ReconciliationPolicy("counts-v1", (), require_review_on_conflict=True),
}


def canonical_mantra_count(passages: Sequence[object]) -> int:
    """Count actual canonical mantra records, never a source's reported total."""
    return sum(1 for passage in passages if getattr(passage, "entity_type", None) == "MANTRA")
