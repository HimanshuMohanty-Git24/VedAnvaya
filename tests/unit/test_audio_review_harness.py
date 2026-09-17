"""The audible-review gate, tested rather than trusted.

Owner decision 4 keeps the 1,021-row listening queue mandatory and forbids any automated
text or metadata check from relabelling a row ``AUDIBLY_VERIFIED``. That prohibition is
worth nothing as a comment, so the harness enforces it at the endpoint and these tests
hold the endpoint to it.

Each test runs against a temporary queue and log, never the real ones: an earlier
hand-probe of these same gates left a self-test decision in the production log, which would
have made "0 of 1,021 reviewed" read as 1 decided. A gate probe that alters the figure it
is probing is the kind of small dishonesty this campaign keeps finding.
"""

from __future__ import annotations

import importlib
import json
import pathlib
from typing import Any

import pytest

harness = importlib.import_module("scripts.audio_review_harness")

QUEUE_ROW: dict[str, Any] = {
    "review_id": "REV-TEST-001",
    "stratum": "TEST",
    "review_priority": 1,
    "canonical_key": "VG:RV:SAK:M01:S001:V001",
    "citation": "RV 1.1.1",
    "canonical_sanskrit": "agním īḷe puróhitaṁ",
    "media_url": "https://example.invalid/a.ogg",
    "review_status": "NEEDS_AUDIBLE_REVIEW",
    "reviewer": None,
    "reviewed_at": None,
    "verdict": None,
    "reviewer_notes": None,
}


@pytest.fixture
def sandbox(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    queue = tmp_path / "queue.jsonl"
    queue.write_text(json.dumps(QUEUE_ROW) + "\n", encoding="utf-8")
    monkeypatch.setattr(harness, "QUEUE", queue)
    monkeypatch.setattr(harness, "LOG", tmp_path / "decisions.jsonl")
    return tmp_path


def test_only_three_verdicts_exist() -> None:
    """A fourth state would be a way to avoid deciding, so the tuple is pinned."""
    assert harness.VERDICTS == (
        "AUDIBLY_VERIFIED",
        "AUDIBLY_REJECTED",
        "AUDIBLE_REVIEW_UNCERTAIN",
    )


def test_a_heard_verdict_requires_audio_and_an_unheard_one_does_not() -> None:
    """The distinction the gate turns on.

    Verified and rejected both assert something about a sound. Uncertain asserts only that
    the reviewer could not decide, which is exactly the answer available when the audio
    would not play -- so requiring audio for it would push a reviewer towards a verdict
    they cannot support.
    """
    assert harness.REQUIRES_AUDIO == {"AUDIBLY_VERIFIED", "AUDIBLY_REJECTED"}
    assert "AUDIBLE_REVIEW_UNCERTAIN" not in harness.REQUIRES_AUDIO


def test_the_log_is_append_only_and_the_queue_is_its_projection(sandbox: pathlib.Path) -> None:
    """Resumability, and which file is the record.

    The queue is rebuilt from the log on every read, latest decision per row winning, so a
    reviewer who changes their mind leaves both entries on the record and the projection
    shows the second one.
    """
    harness.append_decision(
        {
            "review_id": "REV-TEST-001",
            "verdict": "AUDIBLY_REJECTED",
            "reviewer": "first pass",
            "reviewed_at": "2026-09-15T10:00:00+00:00",
            "notes": "wrong verse",
            "listened_seconds": 12.0,
        }
    )
    harness.append_decision(
        {
            "review_id": "REV-TEST-001",
            "verdict": "AUDIBLY_VERIFIED",
            "reviewer": "second pass",
            "reviewed_at": "2026-09-15T11:00:00+00:00",
            "notes": "played the wrong file the first time",
            "listened_seconds": 14.0,
        }
    )

    rows = harness.load_queue()
    assert len(rows) == 1
    assert rows[0]["review_status"] == "AUDIBLY_VERIFIED"
    assert rows[0]["reviewer"] == "second pass"

    # Both decisions survive; the correction did not erase the first judgement.
    logged = harness.read_jsonl(harness.LOG)
    assert [entry["verdict"] for entry in logged] == [
        "AUDIBLY_REJECTED",
        "AUDIBLY_VERIFIED",
    ]

    state = harness.progress(rows)
    assert state == {
        "total": 1,
        "decided": 1,
        "remaining": 0,
        "by_status": {"AUDIBLY_VERIFIED": 1},
        "by_stratum": {"TEST": {"AUDIBLY_VERIFIED": 1}},
        "verdicts": list(harness.VERDICTS),
    }


def test_an_undecided_queue_reports_every_row_remaining(sandbox: pathlib.Path) -> None:
    """The figure the campaign reports, computed the way the campaign reports it."""
    state = harness.progress(harness.load_queue())
    assert state["decided"] == 0
    assert state["remaining"] == state["total"] == 1
    assert state["by_status"] == {"NEEDS_AUDIBLE_REVIEW": 1}


def test_progress_counts_only_the_three_final_states(sandbox: pathlib.Path) -> None:
    """A row in some other state is not decided, however it got there.

    Guards against the failure the owner named directly: a status invented elsewhere in the
    pipeline must not be counted as a completed review.
    """
    harness.append_decision(
        {
            "review_id": "REV-TEST-001",
            "verdict": "TEXT_VERIFIED",
            "reviewer": "a pipeline",
            "reviewed_at": "2026-09-15T12:00:00+00:00",
            "listened_seconds": 0,
        }
    )
    state = harness.progress(harness.load_queue())
    assert state["decided"] == 0, "a non-final status must not count as a review"
    assert state["by_status"] == {"TEXT_VERIFIED": 1}


# --- the queue's own provenance coverage -------------------------------------------------
#
# Wave 4 fixed `source_name` on 804 rows and recorded that every row thereafter carried
# "licence and attribution". It did not. 61 rows -- the RV 1.65-1.70 span stratum, appended
# after that fix -- were built by a second, hand-written row literal that carried neither
# field, and a further 914 carried the `licence` key with a null value. Measuring presence
# of the KEY rather than of a VALUE is what let that read as covered.
#
# These are coverage assertions, not precision assertions: they count how many rows the
# check actually reached, because a validator that silently skips is worse than none.

QUEUE = pathlib.Path("data/staging/audio_review_queue.jsonl")


def _real_queue() -> list[dict[str, Any]]:
    if not QUEUE.exists():  # pragma: no cover - the queue is a committed artifact
        pytest.skip(f"{QUEUE} not built")
    return [json.loads(line) for line in QUEUE.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_queued_row_states_its_rights_position() -> None:
    """No reviewer is shown a blank licence cell.

    A blank reads as "unencumbered", which for 786 of these rows is the opposite of the
    truth: VedSearch publishes no licence statement at all. The absence is typed into the
    row so a researched finding cannot be mistaken for a field nobody filled in.
    """
    rows = _real_queue()
    assert rows, "the queue is empty"
    blank = [r["review_id"] for r in rows if not r.get("licence")]
    assert blank == [], f"{len(blank)} of {len(rows)} rows carry no rights position: {blank[:5]}"
    unattributed = [r["review_id"] for r in rows if "attribution" not in r]
    assert unattributed == [], f"{len(unattributed)} rows lack the attribution field"


def test_rights_coverage_is_measured_over_every_stratum() -> None:
    """Every stratum is reached, so a second row-construction path cannot hide in one.

    The defect this pins was confined to a single stratum. A check that sampled the queue,
    or that stopped at the first stratum, would have passed while 61 rows went out bare.
    """
    rows = _real_queue()
    strata = {str(r.get("stratum")) for r in rows}
    assert len(strata) > 1, "expected several strata; a single-stratum queue hides path bugs"
    for stratum in sorted(strata):
        in_stratum = [r for r in rows if str(r.get("stratum")) == stratum]
        covered = [r for r in in_stratum if r.get("licence")]
        assert len(covered) == len(in_stratum), (
            f"stratum {stratum}: {len(in_stratum) - len(covered)} of {len(in_stratum)} "
            "rows carry no rights position"
        )


def test_no_queued_row_claims_to_have_been_heard() -> None:
    """The campaign figure is 1,021 needing review and 0 decided. Nothing may pre-empt it."""
    rows = _real_queue()
    heard = [r["review_id"] for r in rows if r.get("verdict") or r.get("reviewer")]
    assert heard == [], f"{len(heard)} rows carry a verdict without a human: {heard[:5]}"
    assert {str(r.get("review_status")) for r in rows} == {"NEEDS_AUDIBLE_REVIEW"}
