"""Apply an independent adjudication of the model semantic candidates to the graph.

The enrichment layer proposed 736 semantic assertions -- ``DESCRIBES``, ``INVOKES``,
``REQUESTS`` and nine other predicates -- each extracted by a model from one passage and
landed at ``TIER_D``, meaning *candidate*. All 736 were then reviewed one at a time by an
independent adjudicator that read the passage and checked the Sanskrit, producing
``semantic_candidate_review_v3.jsonl``: 587 accepted, 123 rejected, 16 needing more
evidence, 10 ambiguous.

**That review had never been applied.** Measured against the live graph before this module
existed: all 736 candidate edges were present, all at ``TIER_D``, all with
``review_state`` unset -- so 149 assertions an independent reviewer had *not* accepted
were still live product edges, and the 587 that survived review were indistinguishable
from the ones that failed it. The graph's ``TIER_C`` count was zero, not because nothing
had earned it, but because the earning was never recorded.

Three verdicts, three different actions, and the differences are the point.

``ACCEPT_MODEL_REVIEWED`` -> **promoted to TIER_C.**
    ``TIER_C`` is defined as "model-extracted and independently reviewed and accepted",
    which is exactly what these are. The promotion carries the reviewer, the reviewing
    model, the stated reason and whether the passage was read and the Sanskrit checked, so
    the promotion is auditable rather than asserted. ``review_state`` is set to
    ``MODEL_ADJUDICATED`` and **never** to ``HUMAN_REVIEWED``: no human has read these.

``REJECT`` -> **the edge is deleted.**
    A rejected candidate is one where a reviewer read the passage and concluded the
    assertion is wrong. No tier makes that safe to keep, because the reader who runs the
    obvious query never sees the tier -- which is precisely why a wrong answer with a
    caveat attached is graded ``MISLEADING`` rather than ``PARTIALLY_ANSWERABLE`` in this
    project's benchmark. Deleting is also the established precedent here: the mention
    loader retires edges whose alias was rejected, on the stated ground that this "is what
    makes the lexicon's *rejections* effective rather than advisory". Nothing is lost --
    every one of the 736 rows, verdict and reason included, stays in the artifact on disk
    and the deletion is reproducible from it.

``AMBIGUOUS`` / ``NEEDS_MORE_EVIDENCE`` -> **kept at TIER_D, stamped.**
    These are not rejections. The reviewer could not decide, and ``TIER_D`` already means
    "candidate, unresolved", so the tier is right and only the record of *why* was
    missing. They are stamped with the verdict so a query can exclude them deliberately,
    and they are deliberately not promoted and deliberately not deleted. Collapsing them
    into either neighbouring verdict would destroy the distinction the four-state review
    exists to make.
"""

from __future__ import annotations

import collections
import pathlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

import orjson

#: The verdict vocabulary, closed. A row carrying anything else is a defect in the review
#: artifact and is refused rather than silently treated as one of these.
VERDICT_ACCEPT: Final = "ACCEPT_MODEL_REVIEWED"
VERDICT_REJECT: Final = "REJECT"
VERDICT_AMBIGUOUS: Final = "AMBIGUOUS"
VERDICT_NEEDS_EVIDENCE: Final = "NEEDS_MORE_EVIDENCE"

KNOWN_VERDICTS: Final[frozenset[str]] = frozenset(
    {VERDICT_ACCEPT, VERDICT_REJECT, VERDICT_AMBIGUOUS, VERDICT_NEEDS_EVIDENCE}
)

#: Verdicts that leave the edge in place at TIER_D rather than promoting or deleting it.
VERDICT_RETAINED: Final[frozenset[str]] = frozenset({VERDICT_AMBIGUOUS, VERDICT_NEEDS_EVIDENCE})

#: Never ``HUMAN_REVIEWED``. The adjudicator is a model and the artifact says so; writing
#: the stronger word would make the graph claim a kind of scrutiny it has not had.
REVIEW_STATE_ADJUDICATED: Final = "MODEL_ADJUDICATED"

#: The twelve predicates the candidate set spans. Every write below is scoped to this set
#: and matched on ``candidate_id``, so no edge outside the candidate layer can be reached
#: even if a review row named one.
CANDIDATE_PREDICATES: Final[tuple[str, ...]] = (
    "CONTRASTS_WITH",
    "DESCRIBES",
    "DESCRIBES_ACTION",
    "HAS_THEME",
    "INVOKES",
    "INVOLVES_OFFERING",
    "INVOLVES_RITUAL",
    "INVOLVES_SUBSTANCE",
    "PRAISES",
    "REFERS_TO_NATURAL_PHENOMENON",
    "REFERS_TO_PLACE",
    "REQUESTS",
)


class ReviewArtifactError(ValueError):
    """The review artifact is unusable: unknown verdict, or a row with no candidate."""


class Session(Protocol):
    def run(self, query: str, /, **parameters: Any) -> Any: ...


@dataclass
class ReviewReport:
    """What the adjudication did, counted per action rather than per verdict.

    Verdicts and actions are not one-to-one -- two verdicts share the "retain" action --
    so both are reported. ``promoted``, ``deleted`` and ``retained`` are measured from the
    database after the writes, not inferred from the input.
    """

    rows: int = 0
    verdicts: dict[str, int] = field(default_factory=dict)
    promoted_sent: int = 0
    promoted: int = 0
    deleted_sent: int = 0
    deleted: int = 0
    retained_sent: int = 0
    retained: int = 0
    unmatched: list[str] = field(default_factory=list)
    tier_c_total: int = 0

    #: Named to match :class:`vedagraph.domain.v3_loader.LoadReport` so a driver can
    #: report every V3 step through one code path.
    step: str = "semantic_candidate_review"

    @property
    def sent(self) -> int:
        """Edges this adjudication set out to change, deletions included."""
        return self.promoted_sent + self.deleted_sent + self.retained_sent

    @property
    def landed(self) -> int:
        """Edges it actually changed."""
        return self.promoted + self.deleted + self.retained

    @property
    def complete(self) -> bool:
        return (
            self.promoted == self.promoted_sent
            and self.retained == self.retained_sent
            and self.deleted == self.deleted_sent
            and not self.unmatched
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "rows": self.rows,
            "verdicts": self.verdicts,
            "promoted": {"sent": self.promoted_sent, "landed": self.promoted},
            "deleted": {"sent": self.deleted_sent, "landed": self.deleted},
            "retained": {"sent": self.retained_sent, "landed": self.retained},
            "unmatched_candidate_ids": len(self.unmatched),
            "tier_c_total": self.tier_c_total,
            "complete": self.complete,
        }


def load_review(project_root: pathlib.Path) -> tuple[dict[str, Any], ...]:
    """Read the adjudication artifact, refusing anything it cannot act on.

    Validation is up front and fatal because the alternative is worse: a row with an
    unrecognised verdict that is quietly skipped leaves a candidate edge live and
    unreviewed while the report says every row was processed.
    """
    path = (
        project_root
        / "data"
        / "enrichment"
        / "vedagraph_enrichment_v1"
        / "semantic_candidate_review_v3.jsonl"
    )
    if not path.exists():
        raise ReviewArtifactError(f"review artifact not found: {path}")

    rows: list[dict[str, Any]] = []
    for number, line in enumerate(_lines(path), start=1):
        row = orjson.loads(line)
        candidate_id = row.get("candidate_id")
        if not candidate_id:
            raise ReviewArtifactError(f"{path.name}:{number} has no candidate_id")
        verdict = row.get("verdict")
        if verdict not in KNOWN_VERDICTS:
            raise ReviewArtifactError(
                f"{path.name}:{number} candidate {candidate_id} carries unknown "
                f"verdict {verdict!r}; known: {sorted(KNOWN_VERDICTS)}"
            )
        rows.append(row)

    duplicates = [
        cid
        for cid, count in collections.Counter(r["candidate_id"] for r in rows).items()
        if count > 1
    ]
    if duplicates:
        raise ReviewArtifactError(
            f"{path.name} adjudicates {len(duplicates)} candidate(s) more than once: "
            f"{duplicates[:5]}"
        )
    return tuple(rows)


def _lines(path: pathlib.Path) -> Iterator[bytes]:
    for raw in path.read_bytes().split(b"\n"):
        if raw.strip():
            yield raw


def _stamp_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """The review fields, flattened onto a row the Cypher can UNWIND."""
    return [
        {
            "candidate_id": row["candidate_id"],
            "verdict": row["verdict"],
            "reviewer": row.get("reviewer", REVIEW_STATE_ADJUDICATED),
            "reviewer_model": row.get("reviewer_model", ""),
            "review_reason": row.get("reason", ""),
            "passage_read": bool(row.get("passage_read", False)),
            "sanskrit_checked": bool(row.get("sanskrit_checked", False)),
            "redundant_with_deterministic_layer": bool(
                row.get("redundant_with_deterministic_layer", False)
            ),
        }
        for row in rows
    ]


#: Scoped by relationship type AND by ``candidate_id``. The type list keeps the match
#: index-eligible; the id is what makes it the right edge.
_TYPE_FILTER: Final = " OR ".join(f"r:{name}" for name in CANDIDATE_PREDICATES)

#: ``evidence_basis`` is set from the review, not left as the extraction wrote it, and the
#: reason is specific. Many candidates were extracted from the stored **English
#: translation** -- their evidence quote is Griffith's prose -- so the extraction alone
#: rests on ``TRANSLATION``. The adjudicator then read the passage and, on
#: ``sanskrit_checked`` rows, verified the assertion against the Sanskrit. Two independent
#: paths having fired is exactly what ``MIXED`` means in this ontology, so a
#: Sanskrit-checked acceptance earns it and an unchecked one stays ``TRANSLATION``. This is
#: the one place where a review legitimately changes the evidence basis rather than only
#: the tier, because the review *added* evidence.
_BASIS_CASE: Final = "CASE WHEN row.sanskrit_checked THEN 'MIXED' ELSE 'TRANSLATION' END"

_PROMOTE_QUERY: Final = f"""
UNWIND $rows AS row
MATCH ()-[r]->()
WHERE ({_TYPE_FILTER}) AND r.candidate_id = row.candidate_id
SET r.quality_tier = 'TIER_C',
    r.evidence_basis = {_BASIS_CASE},
    r.knowledge_layer = 'L3_LLM_EXTRACTED',
    r.review_state = $review_state,
    r.reviewer = row.reviewer,
    r.reviewer_model = row.reviewer_model,
    r.review_verdict = row.verdict,
    r.review_reason = row.review_reason,
    r.review_passage_read = row.passage_read,
    r.review_sanskrit_checked = row.sanskrit_checked,
    r.redundant_with_deterministic_layer = row.redundant_with_deterministic_layer,
    r.grade_basis =
      'model-extracted, then independently adjudicated per passage and accepted',
    r.review_run = $review_run
RETURN count(r) AS c
"""

_RETAIN_QUERY: Final = f"""
UNWIND $rows AS row
MATCH ()-[r]->()
WHERE ({_TYPE_FILTER}) AND r.candidate_id = row.candidate_id
SET r.quality_tier = 'TIER_D',
    r.evidence_basis = {_BASIS_CASE},
    r.knowledge_layer = 'L3_LLM_EXTRACTED',
    r.review_state = $review_state,
    r.reviewer = row.reviewer,
    r.reviewer_model = row.reviewer_model,
    r.review_verdict = row.verdict,
    r.review_reason = row.review_reason,
    r.review_passage_read = row.passage_read,
    r.review_sanskrit_checked = row.sanskrit_checked,
    r.grade_basis =
      'model-extracted, independently adjudicated per passage, not resolved',
    r.review_run = $review_run
RETURN count(r) AS c
"""

_DELETE_QUERY: Final = f"""
UNWIND $rows AS row
MATCH ()-[r]->()
WHERE ({_TYPE_FILTER}) AND r.candidate_id = row.candidate_id
DELETE r
RETURN count(*) AS c
"""

_PRESENT_QUERY: Final = f"""
UNWIND $ids AS cid
MATCH ()-[r]->()
WHERE ({_TYPE_FILTER}) AND r.candidate_id = cid
RETURN cid AS cid
"""


def apply_review(
    session: Session, rows: Sequence[dict[str, Any]], *, review_run: str
) -> ReviewReport:
    """Promote, delete or stamp every adjudicated candidate edge.

    ``review_run`` is written onto every touched edge so that a later pass can tell which
    adjudication produced a given state, and so that re-running a *different* review is
    distinguishable from re-running the same one. Re-running the same review is a no-op:
    every write is an idempotent ``SET`` and the delete is scoped to ids that, after the
    first run, no longer match anything.

    ``unmatched`` is a first-class output, not a warning. A review row whose candidate is
    not in the graph means the adjudication and the projection disagree about what the
    candidate layer contains, and that is worth failing a build over -- it is the same
    class of quiet mismatch that ``sent`` versus ``landed`` exists to surface everywhere
    else in this package.
    """
    report = ReviewReport(rows=len(rows))
    report.verdicts = dict(sorted(collections.Counter(row["verdict"] for row in rows).items()))
    if not rows:
        return report

    accepted = _stamp_rows([r for r in rows if r["verdict"] == VERDICT_ACCEPT])
    rejected = _stamp_rows([r for r in rows if r["verdict"] == VERDICT_REJECT])
    retained = _stamp_rows([r for r in rows if r["verdict"] in VERDICT_RETAINED])

    # Which reviewed candidates exist as edges at all. Measured before any write, because
    # the delete would otherwise make its own targets look like they were never there.
    present = {
        record["cid"]
        for record in session.run(_PRESENT_QUERY, ids=[row["candidate_id"] for row in rows])
    }
    # A *rejected* candidate that is absent from the graph is the goal, not a mismatch:
    # after the first run it has been deleted, and on every run after that its absence is
    # the adjudication holding. Counting it as unmatched made a correct second run report
    # itself incomplete -- which would train a reader to ignore the incompleteness flag,
    # the one signal in this package that is supposed to always mean something.
    report.unmatched = sorted(
        row["candidate_id"]
        for row in rows
        if row["candidate_id"] not in present and row["verdict"] != VERDICT_REJECT
    )

    report.promoted_sent = sum(1 for r in accepted if r["candidate_id"] in present)
    report.deleted_sent = sum(1 for r in rejected if r["candidate_id"] in present)
    report.retained_sent = sum(1 for r in retained if r["candidate_id"] in present)

    if accepted:
        session.run(
            _PROMOTE_QUERY,
            rows=accepted,
            review_state=REVIEW_STATE_ADJUDICATED,
            review_run=review_run,
        )
    if retained:
        session.run(
            _RETAIN_QUERY,
            rows=retained,
            review_state=REVIEW_STATE_ADJUDICATED,
            review_run=review_run,
        )
    if rejected:
        session.run(_DELETE_QUERY, rows=rejected)

    report.promoted = _count(
        session,
        f"MATCH ()-[r]->() WHERE ({_TYPE_FILTER}) AND r.review_run = $review_run "
        "AND r.quality_tier = 'TIER_C' RETURN count(r) AS c",
        review_run=review_run,
    )
    report.retained = _count(
        session,
        f"MATCH ()-[r]->() WHERE ({_TYPE_FILTER}) AND r.review_run = $review_run "
        "AND r.review_verdict IN $verdicts RETURN count(r) AS c",
        review_run=review_run,
        verdicts=sorted(VERDICT_RETAINED),
    )
    still_live = _count(
        session,
        f"MATCH ()-[r]->() WHERE ({_TYPE_FILTER}) AND r.candidate_id IN $ids RETURN count(r) AS c",
        ids=[row["candidate_id"] for row in rejected],
    )
    report.deleted = report.deleted_sent - still_live
    report.tier_c_total = _count(
        session, "MATCH ()-[r]->() WHERE r.quality_tier = 'TIER_C' RETURN count(r) AS c"
    )
    return report


def _count(session: Session, query: str, **parameters: Any) -> int:
    record = session.run(query, **parameters).single()
    return int(record["c"]) if record else 0
