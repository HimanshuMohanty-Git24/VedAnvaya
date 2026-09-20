"""The owner's 100-row audible spot-check, held to the two rules that make it worth running.

Rule one: a sample is a sample. ``AUDIBLY_VERIFIED_SAMPLE`` is the number of rows a named
listener accepted, and the rest of the queue stays ``NOT_INDIVIDUALLY_HEARD``. Every test
here that touches the summary checks that the residual is reported and that no arithmetic
turns *n* accepted into 1,021 heard.

Rule two: nothing writes a verdict a human did not type. The tool refuses ``AUDIBLY_VERIFIED``
and ``AUDIBLY_REJECTED`` when the recording was never opened, refuses an unnamed reviewer,
and appends rather than overwrites.

Rule three, added after the first reviewed row: *opened* has to mean audio reached a
player. 80 of the 100 sampled rows point at a VedSearch endpoint that answers with a JSON
document carrying the MP3 as base64, so the old ``webbrowser.open(media_url)`` showed the
reviewer a page of JSON, played nothing, and still unlocked Y. The tests below hold the
gate to a decode and a launch that actually happened -- which is why ``drive`` stubs the
playback seam rather than the browser, and why an assertion that a browser open counts as
having heard something would now be asserting the defect.

Every test runs against a temporary decisions log. An earlier hand-probe of the browser
harness's gates left a self-test decision in the production log, which would have made
"0 of 1,021 reviewed" read as 1 decided -- a gate probe that moves the figure it is probing
is the small dishonesty this campaign keeps finding.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import importlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
from typing import Any, ClassVar

import pytest

sampler = importlib.import_module("scripts.review_audio_sample")
harness = importlib.import_module("scripts.audio_review_harness")

SAMPLE_MANIFEST = pathlib.Path("data/staging/wave4/audio_owner_sample_manifest.json")
REAL_QUEUE = pathlib.Path("data/staging/audio_review_queue.jsonl")

#: The first row the owner was shown, and the one the JSON-wrapper defect surfaced on.
VEDSEARCH_URL = "https://vedsearch.org/api/v1/attachment/audio/atharved/11.5.17/sanskrit"


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
    # So that show() does not read, and resolve_audio does not write, the real cache.
    monkeypatch.setattr(sampler, "CACHE_DIR", tmp_path / "audio_review")
    return tmp_path


def drive(
    monkeypatch: pytest.MonkeyPatch,
    tokens: list[str],
    notes: list[str] | None = None,
    *,
    playable: bool = True,
) -> list[str]:
    """Feed keystrokes and note lines, recording every recording R was asked to play.

    The seam stubbed is ``play`` -- resolve, decode, launch -- because that is what the
    gate now reads. Stubbing ``webbrowser.open`` instead, as this helper used to, would
    let a test pass on the behaviour the tool was fixed for: a page opening and Y
    unlocking. ``playable=False`` stands in for a source that yields no audio.

    Resolution itself is covered further down, against a stubbed network.
    """
    asked: list[str] = []
    keys = iter(tokens)
    note_lines = iter(notes or [""] * 20)

    def fake_play(row: dict[str, Any]) -> tuple[Any, str]:
        asked.append(str(row["media_url"]))
        if not playable:
            return None, "Could not retrieve playable audio:\n    stubbed as unplayable"
        return (
            sampler.Playable(
                path=pathlib.Path("stub-audio.mp3"),
                content_type="audio/mpeg",
                origin="stubbed in a test",
                size=1234,
                sha256="0" * 64,
            ),
            "playing stub-audio.mp3",
        )

    monkeypatch.setattr(sampler, "read_key", lambda typed: next(keys, "q"))
    monkeypatch.setattr(sampler, "play", fake_play)
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(note_lines, ""))
    return asked


def reseed(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Point the sandbox's sample and queue at these rows, and load them."""
    manifest = {"seed": "test-seed", "requested": len(rows), "selected": len(rows), "rows": rows}
    sampler.SAMPLE.write_text(json.dumps(manifest), encoding="utf-8")
    sampler.QUEUE.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return sampler.load_sample()


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
    assert recorded[0]["recording_opened"] is False


def test_accept_is_allowed_once_the_recording_has_played(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = sampler.load_sample()
    asked = drive(monkeypatch, ["r", "y", "q"], notes=["heard it"])

    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert asked == ["https://example.invalid/a.ogg"]
    assert [r["verdict"] for r in recorded] == ["AUDIBLY_VERIFIED"]
    assert recorded[0]["recording_opened"] is True
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

    asked = drive(monkeypatch, ["r", "u", "q"])
    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    assert [r["review_id"] for r in recorded] == ["REV-A", "REV-B"], "resume re-asked a decided row"
    assert asked == ["https://example.invalid/b.ogg"]


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


# ---------------------------------------------------------------------------
# Resolving a recording into something that actually plays
#
# The defect these cover, in one sentence: 80 of the 100 sampled rows point at
# ``vedsearch.org/api/v1/attachment/audio/...``, which answers with a JSON document
# carrying the MP3 as base64 -- so handing that URL to a browser showed the first
# reviewer a page of JSON and played nothing, while the tool recorded the row as opened.
# ---------------------------------------------------------------------------

#: A plausible MP3: an ID3 tag, then frame bytes. Real enough that a magic check passes.
MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" * 16
OGG = b"OggS\x00\x02" + b"\x00" * 58


def vedsearch_document(
    audio: bytes = MP3,
    *,
    content_type: str = "audio/mpeg",
    attachment_name: str = "11.5.17.mp3",
    encoded: str | None = None,
    drop_base64: bool = False,
) -> dict[str, Any]:
    """The wrapper VedSearch really returns, reduced to the fields that matter."""
    document: dict[str, Any] = {
        "attachment_name": attachment_name,
        "content_type": content_type,
        "attachment_content": {"type": "Buffer", "data": list(audio)},
        "attachment_content_base64": (
            base64.b64encode(audio).decode("ascii") if encoded is None else encoded
        ),
    }
    if drop_base64:
        del document["attachment_content_base64"]
    return {"data": document}


def json_response(payload: dict[str, Any]) -> tuple[bytes, str]:
    return json.dumps(payload).encode("utf-8"), "application/json"


@pytest.fixture
def audio_sandbox(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[pathlib.Path, list[pathlib.Path], list[str]]:
    """A temporary cache, a launcher that records instead of playing, and a mute browser.

    Nothing here touches the network or opens a window. The player is the one seam that
    would otherwise make noise on a test machine, and the browser is stubbed so that a
    fallback can be asserted on rather than observed by a human.
    """
    cache = tmp_path / "audio_review"
    launched: list[pathlib.Path] = []
    browsed: list[str] = []
    monkeypatch.setattr(sampler, "CACHE_DIR", cache)
    monkeypatch.setattr(sampler, "ROOT", tmp_path)
    monkeypatch.setattr(sampler, "launch", launched.append)
    monkeypatch.setattr(sampler.webbrowser, "open", lambda url: browsed.append(url) or True)
    return cache, launched, browsed


def stub_fetch(monkeypatch: pytest.MonkeyPatch, body: bytes, content_type: str) -> list[str]:
    """Answer every fetch with one canned response, recording the URLs asked for."""
    asked: list[str] = []

    def fake(url: str) -> tuple[bytes, str]:
        asked.append(url)
        return body, content_type

    monkeypatch.setattr(sampler, "fetch", fake)
    return asked


def stub_failure(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def fake(url: str) -> tuple[bytes, str]:
        raise error

    monkeypatch.setattr(sampler, "fetch", fake)


# ---------------------------------------------------------------------------
# The VedSearch wrapper
# ---------------------------------------------------------------------------


def test_a_vedsearch_json_response_yields_the_real_audio_bytes(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fix itself: JSON in, decoded audio on disk, byte for byte."""
    cache, _, browsed = audio_sandbox
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))
    row = make_row("REV-AV", VEDSEARCH_URL)

    playable = sampler.resolve_audio(row)

    assert playable.path.parent == cache
    assert playable.path.read_bytes() == MP3, "the saved file is not the audio that arrived"
    assert playable.size == len(MP3)
    assert playable.content_type == "audio/mpeg"
    assert playable.sha256 == hashlib.sha256(MP3).hexdigest()
    assert browsed == [], "the JSON document must never be handed to a browser"


def test_an_mpeg_attachment_is_saved_as_mp3(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows picks the player by extension, so a wrong one here is silence."""
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))

    playable = sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))

    assert playable.path.suffix == ".mp3"


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("audio/mpeg", ".mp3"),
        ("audio/mpeg; charset=utf-8", ".mp3"),
        ("audio/ogg", ".ogg"),
        ("audio/wav", ".wav"),
        ("audio/x-wav", ".wav"),
        ("audio/flac", ".flac"),
        ("audio/mp4", ".m4a"),
    ],
)
def test_the_extension_comes_from_the_content_type(content_type: str, expected: str) -> None:
    assert sampler.extension_for(content_type) == expected


def test_the_content_type_outranks_a_disagreeing_filename() -> None:
    """A source naming its file .mp3 while serving Ogg would otherwise write silence."""
    assert sampler.extension_for("audio/ogg", "recitation.mp3") == ".ogg"


def test_an_unhelpful_content_type_falls_back_to_the_filename() -> None:
    assert sampler.extension_for("application/octet-stream", "recitation.ogg") == ".ogg"


#: Four characters of real payload replaced by four outside the base64 alphabet. Strip
#: them -- which is what ``b64decode`` does when it is not validating -- and what remains
#: is still well-formed base64, three audio bytes shorter. So this payload decodes
#: *silently and wrongly* without ``validate=True`` and raises with it, which is the whole
#: reason the flag is there. The obvious test string, ``"!!!! not base64 !!!!"``, does not
#: discriminate: it fails the padding check either way, so it passes against a decoder
#: with no validation at all and proves nothing.
_GOOD_B64 = base64.b64encode(MP3).decode("ascii")
SILENTLY_CORRUPT_B64 = _GOOD_B64[:12] + "!!!!" + _GOOD_B64[16:]


def test_the_corrupt_payload_used_below_is_really_the_discriminating_one() -> None:
    """Pins the premise of the next test, so it cannot quietly stop testing anything."""
    lax = base64.b64decode(SILENTLY_CORRUPT_B64)

    assert lax != MP3, "the lax decode must produce the wrong bytes, not the right ones"
    assert lax, "and it must succeed, or the strict flag is not what does the rejecting"
    with pytest.raises(binascii.Error):
        base64.b64decode(SILENTLY_CORRUPT_B64, validate=True)


@pytest.mark.parametrize(
    "encoded",
    [
        pytest.param(SILENTLY_CORRUPT_B64, id="silently-decodes-to-wrong-bytes"),
        pytest.param("!!!! not base64 !!!!", id="not-base64-at-all"),
        pytest.param("QQ", id="truncated-mid-group"),
    ],
)
def test_malformed_base64_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
    encoded: str,
) -> None:
    """The trap this guards: ``b64decode`` without ``validate`` silently drops every
    character outside the alphabet, so a corrupted payload decodes to plausible garbage
    and is written out under an .mp3 name as though it were a recording."""
    cache, launched, _ = audio_sandbox
    stub_fetch(monkeypatch, *json_response(vedsearch_document(encoded=encoded)))

    with pytest.raises(sampler.AudioUnavailable, match="not valid base64"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))

    assert launched == []
    assert list(cache.glob("*")) == [], "a rejected payload still reached the disk"


def test_a_missing_base64_field_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_fetch(monkeypatch, *json_response(vedsearch_document(drop_base64=True)))

    with pytest.raises(sampler.AudioUnavailable, match="no attachment_content_base64"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


def test_an_empty_base64_field_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_fetch(monkeypatch, *json_response(vedsearch_document(encoded="")))

    with pytest.raises(sampler.AudioUnavailable, match="no attachment_content_base64"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


def test_base64_that_decodes_to_nothing_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid base64 for zero bytes is not a recording."""
    stub_fetch(monkeypatch, *json_response(vedsearch_document(audio=b"")))

    with pytest.raises(sampler.AudioUnavailable, match="no attachment_content_base64"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


def test_a_non_audio_content_type_in_the_attachment_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stated check: ``data.content_type`` must be audio/* before anything is played."""
    stub_fetch(monkeypatch, *json_response(vedsearch_document(content_type="application/pdf")))

    with pytest.raises(sampler.AudioUnavailable, match="not audio/"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


def test_line_wrapped_base64_is_accepted(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrapping is a formatting choice; only a character outside the alphabet is corruption."""
    wrapped = "\n".join(
        base64.b64encode(MP3).decode("ascii")[i : i + 24]
        for i in range(0, len(base64.b64encode(MP3)), 24)
    )
    stub_fetch(monkeypatch, *json_response(vedsearch_document(encoded=wrapped)))

    assert sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL)).path.read_bytes() == MP3


def test_a_json_document_without_a_data_object_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_fetch(monkeypatch, *json_response({"error": "not found"}))

    with pytest.raises(sampler.AudioUnavailable, match="no 'data' object"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


# ---------------------------------------------------------------------------
# The other providers, which must keep working
# ---------------------------------------------------------------------------


def test_a_direct_audio_response_is_saved_as_it_arrived(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VedaWeb serves real .ogg files. 15 of the 100 sampled rows are its, and they must
    not be routed through a decoder that expects a wrapper."""
    _, _, browsed = audio_sandbox
    stub_fetch(monkeypatch, OGG, "audio/ogg")
    row = make_row("REV-RV", "https://vedaweb.uni-koeln.de/media/recitations/rv/k/01.117.06.ogg")

    playable = sampler.resolve_audio(row)

    assert playable.path.read_bytes() == OGG
    assert playable.path.suffix == ".ogg"
    assert playable.content_type == "audio/ogg"
    assert "direct" in playable.origin
    assert browsed == []


def test_a_row_naming_a_local_file_is_played_where_it_lies(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No fetch, no copy into the cache -- and no network stub, so a request would fail."""
    cache, _, _ = audio_sandbox
    on_disk = tmp_path / "already_here.mp3"
    on_disk.write_bytes(MP3)

    playable = sampler.resolve_audio(make_row("REV-LOCAL", str(on_disk)))

    assert playable.path == on_disk
    assert playable.content_type == "audio/mpeg"
    assert list(cache.glob("*")) == [], "a local file was copied into the cache"


def test_a_local_file_that_is_not_there_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]], tmp_path: pathlib.Path
) -> None:
    missing = tmp_path / "gone.mp3"

    with pytest.raises(sampler.AudioUnavailable, match="not there"):
        sampler.resolve_audio(make_row("REV-LOCAL", str(missing)))


def test_a_wikimedia_file_page_is_resolved_to_the_media_behind_it(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Commons ``File:`` URL is HTML around a player. The audio is one redirect away, so
    it is resolved rather than left to the browser fallback."""
    _, _, browsed = audio_sandbox
    asked = stub_fetch(monkeypatch, OGG, "audio/ogg")
    page = "https://commons.wikimedia.org/wiki/File:%E0%A4%A7_Dhenu_sama.ogg"

    playable = sampler.resolve_audio(make_row("REV-SV", page))

    assert asked == ["https://commons.wikimedia.org/wiki/Special:FilePath/%E0%A4%A7_Dhenu_sama.ogg"]
    assert playable.path.read_bytes() == OGG
    assert browsed == []


def test_an_ordinary_web_page_keeps_the_browser_fallback(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one residual case. The browser still opens, because a human may be able to play
    it by hand -- but the row is not marked as played."""
    _, launched, browsed = audio_sandbox
    stub_fetch(monkeypatch, b"<html><body>a page</body></html>", "text/html")
    row = make_row("REV-PAGE", "https://example.invalid/some/page")

    played, message = sampler.play(row)

    assert played is None, "a web page counted as a recording that played"
    assert launched == []
    assert browsed == [row["media_url"]]
    assert "Could not retrieve playable audio:" in message


# ---------------------------------------------------------------------------
# Failure, which must be survivable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (urllib.error.HTTPError("https://x", 404, "Not Found", None, None), "HTTP 404"),
        (urllib.error.HTTPError("https://x", 500, "Server Error", None, None), "HTTP 500"),
        (urllib.error.URLError("getaddrinfo failed"), "could not be reached"),
        (TimeoutError("timed out"), "TimeoutError"),
    ],
)
def test_a_network_failure_is_reported_and_nothing_is_played(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: str,
) -> None:
    cache, launched, browsed = audio_sandbox
    stub_failure(monkeypatch, error)

    played, message = sampler.play(make_row("REV-AV", VEDSEARCH_URL))

    assert played is None
    assert message.startswith("Could not retrieve playable audio:")
    assert expected in message
    assert launched == []
    assert browsed == [], "a failed fetch must not fall back to opening the URL"
    assert not cache.exists() or list(cache.glob("*")) == []


def test_a_response_over_the_cap_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bound on one keystroke, so a change upstream cannot start an unbounded download."""
    monkeypatch.setattr(sampler, "MAX_AUDIO_BYTES", 32)

    class Response:
        headers: ClassVar[dict[str, str]] = {"Content-Type": "audio/mpeg"}

        def read(self, size: int) -> bytes:
            return b"\x00" * size

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

    monkeypatch.setattr(sampler.urllib.request, "urlopen", lambda *a, **k: Response())

    with pytest.raises(sampler.AudioUnavailable, match="review cap"):
        sampler.resolve_audio(make_row("REV-AV", VEDSEARCH_URL))


def test_a_player_that_will_not_open_is_reported_not_raised(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The audio decoded, so the bytes are fine -- but nothing played, so the gate stays shut."""
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))

    def refuse(path: pathlib.Path) -> None:
        raise OSError("no application is associated with this file")

    monkeypatch.setattr(sampler, "launch", refuse)

    played, message = sampler.play(make_row("REV-AV", VEDSEARCH_URL))

    assert played is None
    assert "no player would open it" in message


def test_a_row_with_no_recording_is_refused(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
) -> None:
    played, message = sampler.play(make_row("REV-EMPTY", ""))

    assert played is None
    assert "names no recording" in message


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def test_replay_reuses_the_downloaded_file_instead_of_fetching_again(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R twice must be one request. The reviewer will press it repeatedly on 100 rows."""
    _, launched, _ = audio_sandbox
    asked = stub_fetch(monkeypatch, *json_response(vedsearch_document()))
    row = make_row("REV-AV", VEDSEARCH_URL)

    first, _ = sampler.play(row)
    second, message = sampler.play(row)

    assert first is not None and second is not None
    assert second.path == first.path
    assert len(asked) == 1, f"the recording was fetched {len(asked)} times"
    assert launched == [first.path, first.path], "the second R did not reach the player"
    assert "already downloaded" in message


def test_a_cached_file_is_reused_across_sessions(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resuming the review must not re-download rows heard before the last quit."""
    cache, _, _ = audio_sandbox
    row = make_row("REV-AV", VEDSEARCH_URL)
    cache.mkdir(parents=True)
    (cache / f"{sampler.cache_stem(row)}.mp3").write_bytes(MP3)
    stub_failure(monkeypatch, AssertionError("a cached row must not be fetched"))

    assert sampler.resolve_audio(row).path.read_bytes() == MP3


def test_a_half_written_download_is_never_replayed_as_complete(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interrupting a fetch leaves a .part file, which must not be mistaken for the audio."""
    cache, _, _ = audio_sandbox
    row = make_row("REV-AV", VEDSEARCH_URL)
    cache.mkdir(parents=True)
    (cache / f"{sampler.cache_stem(row)}.mp3.part").write_bytes(b"trunc")
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))

    assert sampler.cached_audio(row) is None
    assert sampler.resolve_audio(row).path.read_bytes() == MP3


def test_an_empty_cached_file_is_not_replayed(
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache, _, _ = audio_sandbox
    row = make_row("REV-AV", VEDSEARCH_URL)
    cache.mkdir(parents=True)
    (cache / f"{sampler.cache_stem(row)}.mp3").write_bytes(b"")
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))

    assert sampler.resolve_audio(row).path.read_bytes() == MP3


def test_the_cache_name_identifies_the_recording_not_the_review_id() -> None:
    """``review_id`` covers four distinct Commons recordings in this queue, so caching by
    id alone would replay the first of them four times under one verdict each."""
    shared = [
        make_row("REV-SV_CONTAINER_SCOPE-VG:SV:KAU:UTTARA:P01:R01", f"https://x.invalid/{n}.ogg")
        for n in "abcd"
    ]
    stems = {sampler.cache_stem(row) for row in shared}

    assert len(stems) == 4, "four recordings collapsed onto fewer cache files"
    assert all("/" not in stem and ":" not in stem for stem in stems), "unsafe filename"


# ---------------------------------------------------------------------------
# The gate, against the real resolution path
# ---------------------------------------------------------------------------


def test_pressing_r_on_a_json_endpoint_then_y_records_nothing_when_it_cannot_decode(
    sandbox: pathlib.Path,
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reported defect end to end. The source answers with JSON that carries no audio;
    R fails; Y must be refused; the row must not advance past unheard."""
    _, launched, browsed = audio_sandbox
    rows, manifest = reseed([make_row("REV-AV", VEDSEARCH_URL)])
    stub_fetch(monkeypatch, *json_response(vedsearch_document(drop_base64=True)))
    keys = iter(["r", "y", "q"])
    monkeypatch.setattr(sampler, "read_key", lambda typed: next(keys, "q"))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")

    sampler.review(rows, manifest, "tester", typed=True)

    assert sampler.read_jsonl(sampler.DECISIONS) == [], "a verdict was recorded on unheard audio"
    assert launched == []
    assert browsed == [], "the JSON metadata page was opened in a browser"


def test_pressing_r_successfully_then_y_records_what_played(
    sandbox: pathlib.Path,
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half: a real decode, a real launch, and a record of the exact file."""
    _, launched, _ = audio_sandbox
    rows, manifest = reseed([make_row("REV-AV", VEDSEARCH_URL)])
    stub_fetch(monkeypatch, *json_response(vedsearch_document()))
    keys = iter(["r", "y", "q"])
    monkeypatch.setattr(sampler, "read_key", lambda typed: next(keys, "q"))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "clear recitation")

    sampler.review(rows, manifest, "tester", typed=True)
    entry = sampler.read_jsonl(sampler.DECISIONS)[0]

    assert entry["verdict"] == "AUDIBLY_VERIFIED"
    assert entry["recording_opened"] is True
    assert entry["audio_content_type"] == "audio/mpeg"
    assert entry["audio_bytes"] == len(MP3)
    assert entry["audio_sha256"] == hashlib.sha256(MP3).hexdigest()
    assert entry["audio_file"].endswith(".mp3")
    assert entry["listened_seconds"] is None, "a terminal cannot measure this; say so"
    assert len(launched) == 1


def test_a_failed_playback_leaves_the_reviewer_on_the_same_row(
    sandbox: pathlib.Path,
    audio_sandbox: tuple[pathlib.Path, list[pathlib.Path], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source being down must not advance the queue, and must not end the session."""
    rows, manifest = reseed(
        [make_row("REV-AV", VEDSEARCH_URL), make_row("REV-B", "https://x.invalid/b.ogg")]
    )
    stub_failure(monkeypatch, urllib.error.URLError("getaddrinfo failed"))
    keys = iter(["r", "r", "u", "q"])
    monkeypatch.setattr(sampler, "read_key", lambda typed: next(keys, "q"))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "would not play")

    sampler.review(rows, manifest, "tester", typed=True)
    recorded = sampler.read_jsonl(sampler.DECISIONS)

    # Two failed Rs, then U on the *first* row -- not on the second.
    assert [r["review_id"] for r in recorded] == ["REV-AV"]
    assert recorded[0]["verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert recorded[0]["recording_opened"] is False
    assert recorded[0]["audio_file"] is None
    assert "no playable audio" in recorded[0]["evidence_of_audio_consumption"]


def test_accept_is_refused_after_a_failed_play(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pressing R is not the gate; R *succeeding* is."""
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, ["r", "y", "n", "q"], playable=False)

    sampler.review(rows, manifest, "tester", typed=True)

    assert sampler.read_jsonl(sampler.DECISIONS) == []


# ---------------------------------------------------------------------------
# The row has to be printable before it can be judged
# ---------------------------------------------------------------------------


def test_showing_the_real_first_row_survives_a_non_utf8_stdout() -> None:
    """Found while smoke-testing the fix: the session died on row 1 before any verdict.

    Every row prints its canonical Sanskrit in IAST, and row 1 of the real sample carries
    U+015B. With stdout on the Windows ANSI code page -- which is what a pipe or a
    redirect gives you -- printing it raised UnicodeEncodeError and unwound the whole
    session, after the recording had played and before a verdict could be typed.

    It has to be a subprocess: the stream encoding is fixed when the interpreter starts,
    so it cannot be faked from inside this one. And it has to render an actual row --
    ``--progress`` prints only counts and stratum names, all of them ASCII, so a test
    pointed at that passes just as happily with the fix taken back out.
    """
    if not (SAMPLE_MANIFEST.exists() and REAL_QUEUE.exists()):  # pragma: no cover
        pytest.skip("sample manifest or queue not built")
    repo = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib;"
            "m = importlib.import_module('scripts.review_audio_sample');"
            "rows, _ = m.load_sample();"
            "m.show(rows[0], 1, len(rows), 0, None)",
        ],
        capture_output=True,
        cwd=repo,
        env={**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
        check=False,
        # The child is handed cp1252, which is the condition under test. This side reads
        # UTF-8 back, because a child that reconfigured itself correctly emits UTF-8 --
        # decoding the pipe as cp1252 fails on the very bytes the fix produces, in the
        # parent, and reports it as an empty stdout and a zero exit.
        encoding="utf-8",
        errors="replace",
    )

    assert "UnicodeEncodeError" not in result.stderr, result.stderr[-800:]
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[-800:]}"
    assert "VG:AV:SAU:K11:S003:V048" in result.stdout, "row 1 did not render"
    assert "Sanskrit (this corpus's text for that key)" in result.stdout
    assert any(ord(ch) > 127 for ch in result.stdout), "the IAST text was stripped to ASCII"


# ---------------------------------------------------------------------------
# The cache stays out of the repository
# ---------------------------------------------------------------------------


def test_the_audio_cache_is_ignored_by_git() -> None:
    """Third-party recitation audio is not this repository's to redistribute, and a
    binary cache in the history would be permanent."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    probe = (sampler.CACHE_DIR.relative_to(repo) / "REV-PROBE__0123456789ab.mp3").as_posix()

    result = subprocess.run(
        ["git", "check-ignore", "-v", probe],
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
    )

    assert result.returncode == 0, f"{probe} is not gitignored ({result.stdout or result.stderr})"


def test_no_audio_file_is_tracked_anywhere_in_the_repository() -> None:
    """The stronger form: not merely ignored, but absent from the index."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "ls-files", "--", "*.mp3", "*.ogg", "*.wav", "*.m4a", "*.flac", ".tmp"],
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
    )

    assert result.stdout.strip() == "", f"audio is tracked:\n{result.stdout}"


# ---------------------------------------------------------------------------
# Correcting a mistyped verdict
#
# The owner reviewed 20 rows and one of them recorded AUDIBLE_REVIEW_UNCERTAIN on an
# accidental keypress: the recording had been played and it matched. Repairing that by
# editing the log would have destroyed the only record of what was actually typed, so the
# repair appends. These tests hold the append to the two properties that make it a
# correction rather than a rewrite -- the original stays readable, and the correction
# invents no second hearing.
# ---------------------------------------------------------------------------


def decide(
    monkeypatch: pytest.MonkeyPatch, tokens: list[str], reviewer: str = "Himanshu"
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one review pass over the sandbox sample and hand back its rows."""
    rows, manifest = sampler.load_sample()
    drive(monkeypatch, tokens, notes=["", ""])
    sampler.review(rows, manifest, reviewer, typed=True)
    return rows, manifest


def no_playback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every route to a recording explode, so a correction cannot quietly take one."""

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a correction reached the playback path")

    monkeypatch.setattr(sampler, "play", forbidden)
    monkeypatch.setattr(sampler, "resolve_audio", forbidden)
    monkeypatch.setattr(sampler, "fetch", forbidden)
    monkeypatch.setattr(sampler, "launch", forbidden)


def test_a_correction_appends_and_leaves_the_original_line_byte_identical(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, _ = decide(monkeypatch, ["r", "u", "q"])
    before = sampler.DECISIONS.read_bytes()

    no_playback(monkeypatch)
    sampler.apply_correction(
        rows,
        review_id="REV-A",
        media_url=None,
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )
    after = sampler.DECISIONS.read_bytes()

    assert after.startswith(before), "the correction rewrote what was already in the log"
    assert len(sampler.read_jsonl(sampler.DECISIONS)) == 2
    assert after[len(before):].count(b"\n") == 1, "more than one line was appended"


def test_the_corrected_verdict_is_the_effective_one(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = decide(monkeypatch, ["r", "u", "q"])
    no_playback(monkeypatch)
    sampler.apply_correction(
        rows,
        review_id="REV-A",
        media_url=None,
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )

    effective = sampler.decisions_by_row()[sampler.row_key(rows[0])]
    summary = sampler.write_summary(rows, manifest)

    assert effective["verdict"] == "AUDIBLY_VERIFIED"
    assert summary["by_verdict"]["AUDIBLE_REVIEW_UNCERTAIN"] == 0, "the mistyped U still counts"
    assert summary["by_verdict"]["AUDIBLY_VERIFIED"] == 1
    assert summary["reviewed"] == 1, "the correction was counted as a second review"
    assert summary["by_stratum"]["TEST"]["AUDIBLE_REVIEW_UNCERTAIN"] == 0


def test_a_correction_carries_the_playback_forward_and_performs_none(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule that keeps a correction from reading as a second listening event."""
    rows, _ = decide(monkeypatch, ["r", "u", "q"])
    original = sampler.read_jsonl(sampler.DECISIONS)[0]

    no_playback(monkeypatch)
    entry = sampler.apply_correction(
        rows,
        review_id="REV-A",
        media_url=None,
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )

    assert entry["new_playback_performed"] is False
    assert entry["playback_provenance"] == "CARRIED_FORWARD_FROM_SUPERSEDED_DECISION"
    # Same recording, not a fresh fetch that happened to agree.
    assert entry["audio_sha256"] == original["audio_sha256"]
    assert entry["audio_file"] == original["audio_file"]
    assert entry["audio_bytes"] == original["audio_bytes"]
    assert entry["reviewed_at"] == original["reviewed_at"], "the correction moved the hearing"
    assert "No new playback" in entry["evidence_of_audio_consumption"]

    # One hearing in the log, two lines.
    log = sampler.read_jsonl(sampler.DECISIONS)
    assert len(log) == 2
    assert sum(1 for e in log if e.get("new_playback_performed") is not False) == 1


def test_the_superseded_verdict_stays_recoverable_from_the_log(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, manifest = decide(monkeypatch, ["r", "u", "q"])
    no_playback(monkeypatch)
    entry = sampler.apply_correction(
        rows,
        review_id="REV-A",
        media_url=None,
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )
    log = sampler.read_jsonl(sampler.DECISIONS)

    # Recoverable two ways: the line itself, and the pointer the correction carries.
    assert log[0]["verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert entry["superseded_verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert entry["corrects_row_key"] == sampler.row_key(rows[0])
    assert log[entry["superseded_decision_line"] - 1] == log[0]
    assert entry["correction_reason"] == "OWNER_CORRECTION_ACCIDENTAL_KEYPRESS"
    assert entry["corrected_at"].endswith("+00:00")
    assert entry["reviewer"] == "Himanshu"

    # And from the summary, so a reader who never opens the log still sees it moved.
    summary = sampler.write_summary(rows, manifest)
    assert summary["corrections_count"] == 1
    assert summary["corrections"][0]["from"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert summary["corrections"][0]["to"] == "AUDIBLY_VERIFIED"
    assert summary["corrections"][0]["new_playback_performed"] is False


def test_correcting_to_verified_is_refused_when_nothing_ever_played(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one that stops a correction from manufacturing a hearing."""
    rows, _ = decide(monkeypatch, ["u", "q"])  # no R: UNCERTAIN with no audio
    assert sampler.read_jsonl(sampler.DECISIONS)[0]["recording_opened"] is False

    no_playback(monkeypatch)
    with pytest.raises(sampler.CorrectionRefused, match="may not supply a playback"):
        sampler.apply_correction(
            rows,
            review_id="REV-A",
            media_url=None,
            to_verdict="AUDIBLY_VERIFIED",
            reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
            reviewer="Himanshu",
        )
    assert len(sampler.read_jsonl(sampler.DECISIONS)) == 1, "a refusal still wrote a line"


def test_a_reason_outside_the_vocabulary_is_refused(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, _ = decide(monkeypatch, ["r", "u", "q"])
    no_playback(monkeypatch)
    with pytest.raises(sampler.CorrectionRefused, match="not a correction reason"):
        sampler.apply_correction(
            rows,
            review_id="REV-A",
            media_url=None,
            to_verdict="AUDIBLY_VERIFIED",
            reason="I_LISTENED_AGAIN",
            reviewer="Himanshu",
        )


def test_somebody_else_correcting_a_row_is_refused(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows, _ = decide(monkeypatch, ["r", "u", "q"], reviewer="Himanshu")
    no_playback(monkeypatch)
    with pytest.raises(sampler.CorrectionRefused, match="a new review, not a correction"):
        sampler.apply_correction(
            rows,
            review_id="REV-A",
            media_url=None,
            to_verdict="AUDIBLY_VERIFIED",
            reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
            reviewer="Someone Else",
        )


def test_a_correction_against_a_changed_sample_is_refused(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A decision taken against one manifest may not be corrected against another."""
    rows, _ = decide(monkeypatch, ["r", "u", "q"])
    manifest = json.loads(sampler.SAMPLE.read_text(encoding="utf-8"))
    manifest["seed"] = "redrawn"
    sampler.SAMPLE.write_text(json.dumps(manifest), encoding="utf-8")

    no_playback(monkeypatch)
    with pytest.raises(sampler.CorrectionRefused, match="The sample changed"):
        sampler.apply_correction(
            rows,
            review_id="REV-A",
            media_url=None,
            to_verdict="AUDIBLY_VERIFIED",
            reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
            reviewer="Himanshu",
        )


def test_an_ambiguous_review_id_is_refused_rather_than_resolved(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``review_id`` is not unique; a bare id covering two decided recordings is a refusal."""
    rows, _ = reseed(
        [
            make_row("REV-SAME", "https://example.invalid/one.ogg"),
            make_row("REV-SAME", "https://example.invalid/two.ogg"),
        ]
    )
    _, manifest = sampler.load_sample()
    drive(monkeypatch, ["r", "u", "r", "u"], notes=["", ""])
    sampler.review(rows, manifest, "Himanshu", typed=True)

    no_playback(monkeypatch)
    with pytest.raises(sampler.CorrectionRefused, match="decided recordings"):
        sampler.apply_correction(
            rows,
            review_id="REV-SAME",
            media_url=None,
            to_verdict="AUDIBLY_VERIFIED",
            reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
            reviewer="Himanshu",
        )

    # Named, it lands on exactly one of the two.
    sampler.apply_correction(
        rows,
        review_id="REV-SAME",
        media_url="https://example.invalid/two.ogg",
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )
    effective = sampler.decisions_by_row()
    assert effective[sampler.row_key(rows[0])]["verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert effective[sampler.row_key(rows[1])]["verdict"] == "AUDIBLY_VERIFIED"


def test_a_correction_promotes_no_other_row(
    sandbox: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One row moves. The queue behind it does not."""
    rows, manifest = sampler.load_sample()
    queue_rows = [
        make_row(f"REV-{n}", f"https://example.invalid/{n}.ogg") for n in range(50)
    ] + rows
    sampler.QUEUE.write_text(
        "\n".join(json.dumps(r) for r in queue_rows) + "\n", encoding="utf-8"
    )
    queue_before = sampler.QUEUE.read_bytes()
    drive(monkeypatch, ["r", "u", "q"], notes=[""])
    sampler.review(rows, manifest, "Himanshu", typed=True)

    no_playback(monkeypatch)
    sampler.apply_correction(
        rows,
        review_id="REV-A",
        media_url=None,
        to_verdict="AUDIBLY_VERIFIED",
        reason="OWNER_CORRECTION_ACCIDENTAL_KEYPRESS",
        reviewer="Himanshu",
    )
    summary = sampler.write_summary(rows, manifest)

    assert sampler.QUEUE.read_bytes() == queue_before, "the correction touched the queue"
    assert len(sampler.decisions_by_row()) == 1, "a second row acquired a verdict"
    assert summary["AUDIBLY_VERIFIED_SAMPLE"] == 1
    assert summary["audible_review_queue_total"] == 52
    assert summary["NOT_INDIVIDUALLY_HEARD"] == 51
    assert all(
        r["review_status"] == "NEEDS_AUDIBLE_REVIEW"
        for r in sampler.read_jsonl(sampler.QUEUE)
    )


# ---------------------------------------------------------------------------
# The live record, not a sandbox
#
# Everything above proves the mechanism. These read the artifacts the owner's review
# actually produced, because a mechanism that works on two synthetic rows and a figure
# that is wrong in the shipped file is the failure this project keeps finding.
# ---------------------------------------------------------------------------

LIVE_DECISIONS = pathlib.Path("data/manual/audio_review/sample_decisions.jsonl")
LIVE_SUMMARY = pathlib.Path("data/manual/audio_review/sample_summary.json")
LIVE_ACCEPTANCE = pathlib.Path("data/manual/audio_review/owner_sample_acceptance.json")


def live_log() -> list[dict[str, Any]]:
    text = LIVE_DECISIONS.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_the_live_sample_is_twenty_reviewed_and_twenty_verified() -> None:
    summary = json.loads(LIVE_SUMMARY.read_text(encoding="utf-8"))

    assert summary["reviewed"] == 20
    assert summary["by_verdict"]["AUDIBLY_VERIFIED"] == 20
    assert summary["by_verdict"]["AUDIBLE_REVIEW_UNCERTAIN"] == 0
    assert summary["by_verdict"]["AUDIBLY_REJECTED"] == 0
    assert summary["AUDIBLY_VERIFIED_SAMPLE"] == 20


def test_the_live_correction_is_one_appended_line_over_twenty_hearings() -> None:
    log = live_log()
    corrections = [e for e in log if e.get("entry_type") == "CORRECTION"]

    assert len(log) == 21, "the log is not 20 decisions plus one correction"
    assert len(corrections) == 1
    assert corrections[0]["superseded_verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert corrections[0]["verdict"] == "AUDIBLY_VERIFIED"
    assert corrections[0]["correction_reason"] == "OWNER_CORRECTION_ACCIDENTAL_KEYPRESS"
    assert corrections[0]["new_playback_performed"] is False
    # 20 recordings heard, 21 lines written. The correction must not read as a 21st.
    assert sum(1 for e in log if e.get("new_playback_performed") is not False) == 20


def test_the_live_superseded_uncertain_is_still_in_the_log() -> None:
    log = live_log()
    correction = next(e for e in log if e.get("entry_type") == "CORRECTION")
    original = log[correction["superseded_decision_line"] - 1]

    assert original["verdict"] == "AUDIBLE_REVIEW_UNCERTAIN"
    assert original["recording_opened"] is True
    assert original["reviewer"] == "Himanshu"
    assert sampler.row_key(original) == correction["corrects_row_key"]
    # The playback the correction leans on is that row's, unchanged.
    assert correction["audio_sha256"] == original["audio_sha256"]


def test_the_live_sample_acceptance_does_not_claim_the_queue_was_heard() -> None:
    acceptance = json.loads(LIVE_ACCEPTANCE.read_text(encoding="utf-8"))

    assert acceptance["AUDIO_OWNER_SAMPLE"] == "ACCEPTED"
    assert acceptance["SAMPLE_REVIEWED"] == 20
    assert acceptance["SAMPLE_VERIFIED"] == 20
    assert acceptance["SAMPLE_UNCERTAIN"] == 0
    assert acceptance["SAMPLE_REJECTED"] == 0
    assert acceptance["scope"]["rows_promoted_by_this_decision"] == 0
    assert acceptance["scope"]["remaining_recordings_status"] == "NOT_INDIVIDUALLY_HEARD"
    assert acceptance["scope"]["remaining_recordings"] == 1001
    assert acceptance["scope"]["queue_total"] == 1021


def test_the_live_acceptance_promoted_no_queue_row() -> None:
    """Sample-level, and the queue is the file that proves it."""
    queue = [
        json.loads(line)
        for line in REAL_QUEUE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    heard = {sampler.row_key(e) for e in live_log()}

    assert len(queue) == 1021
    assert all(r["review_status"] == "NEEDS_AUDIBLE_REVIEW" for r in queue)
    unheard = [r for r in queue if sampler.row_key(r) not in heard]
    assert len(unheard) == 1001, "the heard set does not account for exactly 20 queue rows"
    assert not any("AUDIBLY_VERIFIED" in json.dumps(r) for r in unheard)
