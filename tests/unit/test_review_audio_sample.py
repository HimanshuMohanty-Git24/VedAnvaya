"""The owner's 100-row audible spot-check, held to the two rules that make it worth running.

Rule one: a sample is a sample. ``AUDIBLY_VERIFIED_SAMPLE`` is the number of rows a named
listener accepted, and the rest of the queue stays ``NOT_INDIVIDUALLY_HEARD``. Every test
here that touches the summary checks that the residual is reported and that no arithmetic
turns *n* accepted into 1,021 heard.

Rule two: nothing writes a verdict a human did not type. The tool refuses ``AUDIBLY_VERIFIED``
and ``AUDIBLY_REJECTED`` when the recording was never opened, refuses an unnamed reviewer,
and appends rather than overwrites.

Every test runs against a temporary decisions log. An earlier hand-probe of the browser
harness's gates left a self-test decision in the production log, which would have made
"0 of 1,021 reviewed" read as 1 decided -- a gate probe that moves the figure it is probing
is the small dishonesty this campaign keeps finding.
"""

from __future__ import annotations

import importlib
import json
import pathlib
from typing import Any

import pytest

sampler = importlib.import_module("scripts.review_audio_sample")
harness = importlib.import_module("scripts.audio_review_harness")

SAMPLE_MANIFEST = pathlib.Path("data/staging/wave4/audio_owner_sample_manifest.json")
REAL_QUEUE = pathlib.Path("data/staging/audio_review_queue.jsonl")


def _queue_rows() -> list[dict[str, Any]]:
    text = REAL_QUEUE.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def make_row(review_id: str, media_url: str, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "review_id": review_id,
        "media_url": media_url,
        "stratum": "TEST",
        "review_priority": 1,
        "canonical_key": "VG:RV:SAK:M01:S001:V001",
        "citation": "RV 1.1.1",
        "canonical_sanskrit": "agnim ile purohitam",
        "source_name": "TestSource",
        "listen_for": "is this the mapped verse?",
        "review_status": "NEEDS_AUDIBLE_REVIEW",
    }
    row.update(extra)
    return row


@pytest.fixture
def sandbox(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A two-row sample and an empty log, both temporary."""
    rows = [
        make_row("REV-A", "https://example.invalid/a.ogg"),
        make_row("REV-B", "https://example.invalid/b.ogg"),
    ]
    manifest = tmp_path / "sample.json"
    manifest.write_text(
        json.dumps({"seed": "test-seed", "requested": 2, "selected": 2, "rows": rows}),
        encoding="utf-8",
    )
    queue = tmp_path / "queue.jsonl"
    queue.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    monkeypatch.setattr(sampler, "SAMPLE", manifest)
    monkeypatch.setattr(sampler, "QUEUE", queue)
    monkeypatch.setattr(sampler, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(sampler, "DECISIONS", tmp_path / "out" / "sample_decisions.jsonl")
    monkeypatch.setattr(sampler, "SUMMARY", tmp_path / "out" / "sample_summary.json")
    monkeypatch.setattr(sampler, "ROOT", tmp_path)
    return tmp_path


def drive(
    monkeypatch: pytest.MonkeyPatch, tokens: list[str], notes: list[str] | None = None
) -> list[str]:
    """Feed keystrokes and note lines, recording every URL the tool tried to open."""
    opened: list[str] = []
    keys = iter(tokens)
    note_lines = iter(notes or [""] * 20)
    monkeypatch.setattr(sampler, "read_key", lambda typed: next(keys, "q"))
    monkeypatch.setattr(sampler.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(note_lines, ""))
    return opened


# ---------------------------------------------------------------------------
# The identity a decision attaches to
# ---------------------------------------------------------------------------


def test_review_id_is_not_unique_in_the_real_queue() -> None:
    """The defect the row key exists for, pinned against the artifact that carries it.

    ``REV-SV_CONTAINER_SCOPE-VG:SV:KAU:UTTARA:P01:R01`` covers four distinct Commons
    recordings. If this ever becomes false the key may be simplified -- but it must be a
    decision, not a silent regression back to one verdict covering four unheard files.
    """
    if not REAL_QUEUE.exists():  # pragma: no cover - the queue is a committed artifact
        pytest.skip("audio review queue not built")
    rows = _queue_rows()
    ids = [r["review_id"] for r in rows]
    keys = [sampler.row_key(r) for r in rows]

    assert len(set(ids)) < len(rows), "review_id is now unique; revisit the row key deliberately"
    assert len(set(keys)) == len(rows), "review_id + media_url must identify a row uniquely"


def test_the_harness_keys_decisions_the_same_way() -> None:
    """One shared definition, so the two tools cannot disagree about what a row is."""
    row = {"review_id": "REV-X", "media_url": "https://example.invalid/x.ogg"}

    assert harness.row_key(row) == sampler.row_key(row)


def test_a_verdict_lands_on_one_recording_not_all_four(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bug itself: one keystroke must not verify three recordings nobody played."""
    shared = [
        {"review_id": "REV-SHARED", "media_url": f"https://example.invalid/{n}.ogg"}
        for n in "abcd"
    ]
    queue = tmp_path / "queue.jsonl"
    queue.write_text("\n".join(json.dumps(r) for r in shared) + "\n", encoding="utf-8")
    log = tmp_path / "decisions.jsonl"
    log.write_text(
        json.dumps(
            {
                "review_id": "REV-SHARED",
                "media_url": "https://example.invalid/a.ogg",
                "verdict": "AUDIBLY_VERIFIED",
                "reviewer": "tester",
                "reviewed_at": "2026-09-18T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(harness, "QUEUE", queue)
    monkeypatch.setattr(harness, "LOG", log)

    landed = harness.load_queue()
    verified = [r for r in landed if r.get("review_status") == "AUDIBLY_VERIFIED"]

    assert len(verified) == 1, "a verdict reached a recording that was never played"
    assert verified[0]["media_url"] == "https://example.invalid/a.ogg"
    # The other three must carry no verdict of any kind, not merely a different one.
    others = [r for r in landed if r["media_url"] != "https://example.invalid/a.ogg"]
    assert len(others) == 3
    assert all(r.get("verdict") is None and r.get("reviewer") is None for r in others)


# ---------------------------------------------------------------------------
# The sample itself
# ---------------------------------------------------------------------------


def test_the_real_sample_still_matches_the_live_queue() -> None:
    """Reuse requires the sample to still point at the recordings it was drawn over."""
    if not (SAMPLE_MANIFEST.exists() and REAL_QUEUE.exists()):  # pragma: no cover
        pytest.skip("sample manifest or queue not built")
    rows, manifest = sampler.load_sample()  # raises SystemExit if a row moved

    assert len(rows) == manifest["selected"] == 100
    assert manifest["seed"] == "vedanvaya-wave4-audio-sample"


def test_the_real_sample_is_stratified_across_every_queue_stratum() -> None:
    """A sample that missed a stratum would spot-check a population it never entered."""
    if not (SAMPLE_MANIFEST.exists() and REAL_QUEUE.exists()):  # pragma: no cover
        pytest.skip("sample manifest or queue not built")
    rows, _ = sampler.load_sample()
    queue = _queue_rows()

    assert {r["stratum"] for r in rows} == {r["stratum"] for r in queue}


def test_no_sampled_row_arrives_carrying_a_verdict() -> None:
    """Nothing prefills a human decision, which is the whole point of the queue."""
    if not (SAMPLE_MANIFEST.exists() and REAL_QUEUE.exists()):  # pragma: no cover
        pytest.skip("sample manifest or queue not built")
    rows, _ = sampler.load_sample()

    assert [r for r in rows if r.get("verdict") or r.get("reviewer")] == []
    assert {r["review_status"] for r in rows} == {"NEEDS_AUDIBLE_REVIEW"}


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_accept_is_refused_until_the_recording_is_opened(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["y", "q"])

    sampler.review(rows, manifest, "tester", typed=True)

    assert sampler.read_jsonl(sampler.DECISIONS) == [], "a verdict was recorded without audio"


def test_reject_is_refused_until_the_recording_is_opened(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["n", "q"])

    sampler.review(rows, manifest, "tester", typed=True)

    assert sampler.read_jsonl(sampler.DECISIONS) == []


def test_uncertain_is_reachable_with_no_audio(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The honest answer when a recording will not play must not be the inconvenient one."""
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["u", "q"])

    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert [r["verdict"] for r in recorded] == ["AUDIBLE_REVIEW_UNCERTAIN"]
    assert recorded[0]["audio_opened_in_this_session"] is False


def test_accept_is_allowed_once_the_recording_has_been_opened(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    opened = drive(monkeypatch, ["r", "y", "q"], notes=["heard it"])

    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert opened == ["https://example.invalid/a.ogg"]
    assert [r["verdict"] for r in recorded] == ["AUDIBLY_VERIFIED"]
    assert recorded[0]["audio_opened_in_this_session"] is True
    assert recorded[0]["notes"] == "heard it"
    assert recorded[0]["listened_seconds"] is None, "a terminal cannot measure this; say so"


def test_only_the_three_verdicts_exist() -> None:
    assert set(sampler.VERDICTS) == set(harness.VERDICTS)
    assert set(sampler.WORDS.values()) | set(sampler.KEYS.values()) == set(sampler.VERDICTS)


def test_typed_words_and_single_keys_reach_the_same_verdicts() -> None:
    """Windows raw-key capture is unreliable, so the typed path must be equivalent."""
    for key, word in (("y", "yes"), ("n", "no"), ("u", "uncertain")):
        assert sampler.resolve(key) == sampler.resolve(word)
    assert sampler.resolve("banana") is None


def test_skip_records_nothing(sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["s", "s"])

    sampler.review(rows, manifest, "tester", typed=True)

    assert sampler.read_jsonl(sampler.DECISIONS) == []


# ---------------------------------------------------------------------------
# Resume, and the append-only log
# ---------------------------------------------------------------------------


def test_resume_continues_at_the_next_undecided_row(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["u", "q"])
    sampler.review(rows, manifest, "tester", typed=True)

    opened = drive(monkeypatch, ["r", "u", "q"])
    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert [r["review_id"] for r in recorded] == ["REV-A", "REV-B"], "resume re-asked a decided row"
    assert opened == ["https://example.invalid/b.ogg"]


def test_a_second_verdict_appends_and_never_overwrites(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed mind leaves both judgements on the record; the latest wins the projection."""
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["u", "q"])
    sampler.review(rows, manifest, "tester", typed=True)

    drive(monkeypatch, ["r", "y", "q"])
    sampler.review(rows, manifest, "tester", typed=True, redo=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert len(recorded) == 2, "the earlier verdict was overwritten"
    assert [r["verdict"] for r in recorded] == ["AUDIBLE_REVIEW_UNCERTAIN", "AUDIBLY_VERIFIED"]
    assert sampler.decisions_by_row()[sampler.row_key(rows[0])]["verdict"] == "AUDIBLY_VERIFIED"


def test_every_decision_carries_a_reviewer_a_timestamp_and_the_manifest_digest(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["u", "q"])

    sampler.review(rows, manifest, "Himanshu", typed=True)
    entry = sampler.read_jsonl(sampler.DECISIONS)[0]

    assert entry["reviewer"] == "Himanshu"
    assert entry["reviewed_at"].endswith("+00:00")
    assert entry["sample_manifest_sha256"] == sampler.sample_digest()
    assert entry["media_url"] and entry["canonical_key"]


# ---------------------------------------------------------------------------
# What the summary may claim
# ---------------------------------------------------------------------------


def test_the_summary_reports_the_sample_figure_and_the_unheard_residual(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["r", "y", "r", "y"], notes=["", ""])
    sampler.review(rows, manifest, "tester", typed=True)

    summary = json.loads(sampler.SUMMARY.read_text(encoding="utf-8"))

    assert summary["AUDIBLY_VERIFIED_SAMPLE"] == 2
    assert summary["sample_size"] == 2
    # Two rows in this sandbox queue, both reviewed, so nothing is left unheard here --
    # the field must still exist and be computed rather than assumed away.
    assert summary["NOT_INDIVIDUALLY_HEARD"] == 0
    assert "may not be reported as" in summary["what_this_does_not_establish"]


def test_an_accepted_sample_is_never_reported_as_the_whole_queue(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule the brief states in capitals, as an assertion rather than a comment."""
    rows, manifest = sampler.load_sample()
    # A queue far larger than the sample, so the residual cannot be zero by accident.
    queue_rows = [
        make_row(f"REV-{n}", f"https://example.invalid/{n}.ogg") for n in range(50)
    ] + rows
    sampler.QUEUE.write_text(
        "\n".join(json.dumps(r) for r in queue_rows) + "\n", encoding="utf-8"
    )
    drive(monkeypatch, ["r", "y", "r", "y"], notes=["", ""])
    sampler.review(rows, manifest, "tester", typed=True)

    summary = json.loads(sampler.SUMMARY.read_text(encoding="utf-8"))

    assert summary["AUDIBLY_VERIFIED_SAMPLE"] == 2
    assert summary["audible_review_queue_total"] == 52
    assert summary["NOT_INDIVIDUALLY_HEARD"] == 50
    assert summary["AUDIBLY_VERIFIED_SAMPLE"] != summary["audible_review_queue_total"]


def test_the_summary_breaks_down_by_stratum(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["u", "q"])
    sampler.review(rows, manifest, "tester", typed=True)

    summary = json.loads(sampler.SUMMARY.read_text(encoding="utf-8"))

    assert summary["by_stratum"]["TEST"]["rows"] == 2
    assert summary["by_stratum"]["TEST"]["AUDIBLE_REVIEW_UNCERTAIN"] == 1
    assert summary["by_stratum"]["TEST"]["undecided"] == 1


def test_a_sample_row_that_left_the_queue_stops_the_tool(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better to refuse than to show a reviewer a recording the product no longer maps."""
    sampler.QUEUE.write_text(
        json.dumps(make_row("REV-A", "https://example.invalid/a.ogg")) + "\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit, match="no longer matches the queue"):
        sampler.load_sample()
