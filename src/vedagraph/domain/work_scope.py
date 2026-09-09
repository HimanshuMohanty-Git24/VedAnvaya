"""Project each ``Work``'s corpus scope onto the ``Work`` node itself.

**Why this module exists.** Four `Work` nodes carried seven properties each --
``work_id``, ``work_name``, ``display_label``, ``display_type``, ``veda``,
``abbreviation``, ``corpus_dir`` -- and not one of them said what the corpus *is*. The
Sāmavedic node read ``work_name: "Samaveda Samhita"`` over a corpus that is the Kauthuma
ārcika only, roughly 1,875 verses against a gāna body of some 2,639 ganas that this
work_id cannot address. The corpus's own manifest says *"Never describe this dataset as
the complete Samaveda."* That warning lived in a JSON file on disk; the graph a consumer
actually queries did not have it, which made it the single most misleading string in the
product graph.

**Why an overlay rather than an edit.** ``work_name`` is projected from
``data/canonical/*/works.jsonl``, and those files are hashed into their corpus manifest's
``generated_files`` block. Rewriting the name in place would break the manifest hash and
would also destroy a true fact -- *Sāmaveda Saṃhitā* is the work's traditional name. So
the traditional name is left exactly as the artifact records it and the honest product
label is written beside it as ``display_label``, from
``data/registry/works.yaml``, which no manifest hashes. Fixing this by overlay outside
the seal rather than in place is the rule this repository learned the hard way.

**Why ``completeness`` sits beside the existing ``coverage_status``.** They fail
independently and neither substitutes for the other. ``coverage_status`` is a verdict
(``COMPLETE`` / ``INCOMPLETE_BOUNDED``) and has nowhere to put the numbers that justify
it; ``completeness`` is the measured figure with its shortfall enumerated. A reader who
gets only the verdict cannot tell a 98.3% corpus with 31 enumerated gaps from a corpus
that is complete, and a reader who gets only the numbers cannot tell whether the project
considers the gap bounded.

``excluded_corpora`` is the same fact as ``scope`` in a form a query can filter on. A
``scope`` sentence is for a human reading one row; a list is what a query needs when it
has to decide whether a zero for one Veda means "absent from the text" or "outside this
work_id entirely".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from vedagraph.models import Work


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


@dataclass
class WorkScopeReport:
    """Rows sent against rows that actually landed."""

    step: str = "work_scope"
    sent: int = 0
    landed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.landed >= self.sent

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "detail": self.detail,
        }


#: Properties this loader owns. Named as a constant so the verification query and the
#: write cannot drift apart -- a projection that sets five fields and verifies four is
#: how a partial landing reports success.
SCOPE_PROPERTIES: tuple[str, ...] = (
    "scope",
    "completeness",
    "excluded_corpora",
    "rights",
    "scope_evidence",
)

_SCOPE_QUERY = """
UNWIND $rows AS row
MATCH (w:Work {work_id: row.work_id})
SET w.scope = row.scope,
    w.completeness = row.completeness,
    w.excluded_corpora = row.excluded_corpora,
    w.rights = row.rights,
    w.scope_evidence = row.scope_evidence,
    w.scope_source = 'data/registry/works.yaml',
    w.display_label_override = row.display_label_override,
    w.display_label = coalesce(row.display_label_override, w.work_name, w.abbreviation)
RETURN count(w) AS c
"""
# ``display_label_override`` is written onto the node as well as applied, so that
# ``upgrade.set_display_properties`` -- which recomputes every product node's label from
# ``_DISPLAY_SOURCES`` -- can coalesce the override first and the two loaders become
# order-independent. Without that, whichever ran last would win, and the scope-honest
# label would silently revert to "Samaveda Samhita" on the next projection.
# SET, not ON CREATE SET: every field is derived from the registry, so preserving an
# existing value would freeze a stale scope statement through a rebuild that reported
# success. MATCH, not MERGE, and matched on a labelled pattern with an indexed key --
# this loader must never mint a Work node. An unlabelled MATCH in a mutation once created
# 39,461 bogus edges in this graph, and a MERGE here would silently invent a fifth Veda
# from a typo in a work_id.


def rows_from_works(works: list[Work]) -> list[dict[str, Any]]:
    """Turn registry ``Work`` records into projection rows, skipping unscoped works.

    A work with no ``scope`` is skipped rather than written as null. Writing the null
    would be indistinguishable from the defect this module exists to fix, and would make
    ``count(w.scope)`` useless as a coverage measure.
    """
    return [
        {
            "work_id": work.work_id,
            "scope": work.scope,
            "completeness": work.completeness,
            "excluded_corpora": list(work.excluded_corpora),
            "rights": work.rights,
            "scope_evidence": work.scope_evidence,
            "display_label_override": work.display_label_override,
        }
        for work in works
        if work.scope
    ]


def load_work_scope(session: Session, works: list[Work]) -> WorkScopeReport:
    """Write scope, completeness, exclusions and rights onto the four ``Work`` nodes.

    Idempotent: re-running converges because every field is overwritten from the registry
    and ``display_label`` is recomputed from the override rather than appended to.
    """
    rows = rows_from_works(works)
    report = WorkScopeReport(sent=len(rows))
    if not rows:
        return report

    session.run(_SCOPE_QUERY, rows=rows)

    # Verify per property rather than per node. A single count of matched nodes would
    # report 4/4 even if one property had failed to land on all of them.
    for prop in SCOPE_PROPERTIES:
        record = session.run(
            f"MATCH (w:Work) WHERE w.{prop} IS NOT NULL RETURN count(w) AS c"
        ).single()
        report.detail[prop] = int(record["c"]) if record else 0

    record = session.run(
        "MATCH (w:Work) WHERE w.scope IS NOT NULL AND w.completeness IS NOT NULL "
        "AND w.excluded_corpora IS NOT NULL AND w.rights IS NOT NULL "
        "RETURN count(w) AS c"
    ).single()
    report.landed = int(record["c"]) if record else 0

    overridden = session.run(
        "MATCH (w:Work) WHERE w.display_label <> w.work_name RETURN count(w) AS c"
    ).single()
    report.detail["display_label_overridden"] = int(overridden["c"]) if overridden else 0
    return report


def unscoped_works(session: Session) -> list[str]:
    """``work_id``s of Work nodes still carrying no scope. Empty is the pass condition."""
    return [
        str(record["work_id"])
        for record in session.run(
            "MATCH (w:Work) WHERE w.scope IS NULL RETURN w.work_id AS work_id ORDER BY work_id"
        )
    ]
