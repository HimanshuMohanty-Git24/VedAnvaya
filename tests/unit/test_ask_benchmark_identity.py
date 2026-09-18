"""The benchmark's run identity, and the one thing a credential rotation must not move.

A resumed run is only valid if nothing that changes what the model writes moved between
batches, so ``RunIdentity`` hashes benchmark version, question-set digest, provider, model,
code commit and generation config. *Which account paid* is not in that list and must never
enter it: the whole point of failover is that the owner's second key continues the same
run rather than starting a second one whose 24 answers can never be merged with the first
36.

These tests are the pin on that. They also hold the two resume properties the failover
design leans on -- an answered question is never asked again, and a batch continues at the
first unanswered one -- because rotation is only safe if resumption is exact.
"""

from __future__ import annotations

import importlib
import json
import pathlib
from typing import Any

import pytest
from pydantic import SecretStr

from vedagraph.llm import redaction
from vedagraph.llm.config import LLMSettings

benchmark = importlib.import_module("scripts.run_ask_benchmark")

KEY_1 = "sk-SLOT1-must-never-appear-1a2b3c"
KEY_2 = "sk-SLOT2-must-never-appear-4d5e6f"


def settings(**overrides: Any) -> LLMSettings:
    base: dict[str, Any] = {
        "vedagraph_llm_provider": "openrouter",
        "vedagraph_llm_model": "test/model-v1",
        "vedagraph_llm_api_key": SecretStr(KEY_1),
        "vedagraph_llm_temperature": 0.1,
        "vedagraph_llm_max_output_tokens": 4096,
        "google_api_key": None,
        "gemini_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
    }
    base.update(overrides)
    return LLMSettings(_env_file=None, **base)


class StubProvider:
    """Only the two fields ``build_identity`` reads off a provider."""

    def __init__(self, name: str = "openrouter", model: str = "test/model-v1") -> None:
        self._name, self._model = name, model

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model


def identity_with(monkeypatch: pytest.MonkeyPatch, configured: LLMSettings) -> Any:
    monkeypatch.setattr(benchmark, "get_llm_settings", lambda: configured)
    monkeypatch.setattr(benchmark, "_code_commit", lambda: "abc1234")
    return benchmark.build_identity(StubProvider(), question_set_hash="deadbeef")


# ---------------------------------------------------------------------------
# Run identity is credential-independent
# ---------------------------------------------------------------------------


def test_changing_only_the_credential_changes_neither_config_hash_nor_run_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The property failover depends on, asserted rather than assumed."""
    first = identity_with(monkeypatch, settings(vedagraph_llm_api_key=SecretStr(KEY_1)))
    second = identity_with(monkeypatch, settings(vedagraph_llm_api_key=SecretStr(KEY_2)))

    assert first.config_hash == second.config_hash
    assert first.run_id == second.run_id
    assert first.as_dict() == second.as_dict()


def test_no_credential_appears_anywhere_in_the_run_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = identity_with(monkeypatch, settings())
    rendered = json.dumps(identity.as_dict()) + identity.run_id

    assert KEY_1 not in rendered
    assert KEY_1[:6] not in rendered


def test_adding_a_second_credential_does_not_fork_the_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuring failover mid-run must not orphan the questions already answered."""
    monkeypatch.delenv("OPENROUTER_API_KEY_2", raising=False)
    before = identity_with(monkeypatch, settings())

    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)
    after = identity_with(monkeypatch, settings())

    assert before.run_id == after.run_id


@pytest.mark.parametrize(
    ("field", "value"),
    [("vedagraph_llm_temperature", 0.9), ("vedagraph_llm_max_output_tokens", 2048)],
)
def test_a_generation_knob_does_change_the_run_id(
    field: str, value: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The converse, so the test above is not passing because nothing is hashed at all."""
    base = identity_with(monkeypatch, settings())
    moved = identity_with(monkeypatch, settings(**{field: value}))

    assert base.run_id != moved.run_id


@pytest.mark.parametrize(
    ("name", "model"),
    [("groq", "test/model-v1"), ("openrouter", "test/model-v2")],
    ids=["provider", "model"],
)
def test_the_provider_and_the_model_still_change_the_run_id(
    name: str, model: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both are read off the built provider rather than off settings, so both are tested
    through one. A settings-only parametrize passed while changing nothing, which is what
    a control case is for."""
    monkeypatch.setattr(benchmark, "get_llm_settings", lambda: settings())
    monkeypatch.setattr(benchmark, "_code_commit", lambda: "abc1234")
    base = benchmark.build_identity(StubProvider(), "deadbeef")
    moved = benchmark.build_identity(StubProvider(name=name, model=model), "deadbeef")

    assert base.run_id != moved.run_id


def test_the_question_set_and_the_code_commit_still_change_the_run_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(benchmark, "get_llm_settings", lambda: settings())
    monkeypatch.setattr(benchmark, "_code_commit", lambda: "abc1234")
    base = benchmark.build_identity(StubProvider(), "deadbeef")
    other_questions = benchmark.build_identity(StubProvider(), "feedface")
    monkeypatch.setattr(benchmark, "_code_commit", lambda: "def5678")
    other_commit = benchmark.build_identity(StubProvider(), "deadbeef")

    assert base.run_id != other_questions.run_id
    assert base.run_id != other_commit.run_id


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


@pytest.fixture
def checkpoint_dir(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    monkeypatch.setattr(benchmark, "CHECKPOINT_DIR", tmp_path)
    return tmp_path


def make_identity() -> Any:
    return benchmark.RunIdentity(
        benchmark_version="ask_benchmark_v1",
        question_set_hash="deadbeef",
        provider="openrouter",
        model="test/model-v1",
        code_commit="abc1234",
        config_hash="cafe1234",
    )


def test_an_answered_question_is_never_asked_again(checkpoint_dir: pathlib.Path) -> None:
    identity = make_identity()
    for qid in ("q1", "q2"):
        benchmark.append_checkpoint(identity, {**identity.as_dict(), "id": qid, "answer": "a"})

    done = benchmark.load_checkpoint(identity)
    cases = [{"id": f"q{n}"} for n in range(1, 6)]
    remaining = [c for c in cases if c["id"] not in done]

    assert sorted(done) == ["q1", "q2"]
    assert [c["id"] for c in remaining] == ["q3", "q4", "q5"], "resume skipped or re-spent a row"


def test_resume_across_a_credential_rotation_reads_the_same_checkpoint(
    checkpoint_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """36 answers on slot 1 and 24 on slot 2 are one run of 60, in one file."""
    identity = make_identity()
    for qid in (f"q{n}" for n in range(1, 37)):
        benchmark.append_checkpoint(identity, {**identity.as_dict(), "id": qid, "answer": "a"})

    # A rotation changes nothing the identity is built from, so the identity is equal.
    after_rotation = make_identity()
    assert benchmark.checkpoint_path(after_rotation) == benchmark.checkpoint_path(identity)
    assert len(benchmark.load_checkpoint(after_rotation)) == 36


def test_a_checkpoint_from_a_different_run_is_refused_and_never_merged(
    checkpoint_dir: pathlib.Path,
) -> None:
    """Merging two providers' answers would report a score describing neither."""
    identity = make_identity()
    path = benchmark.checkpoint_path(identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"run_id": "some-other-run", "id": "q1"}) + "\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit, match="never merged"):
        benchmark.load_checkpoint(identity)


def test_no_checkpoint_row_carries_a_credential(checkpoint_dir: pathlib.Path) -> None:
    """Whatever else lands in a row, a key does not."""
    redaction.register_secrets([KEY_1, KEY_2])
    identity = make_identity()
    benchmark.append_checkpoint(
        identity, {**identity.as_dict(), "id": "q1", "answer": "Indra is a deity."}
    )

    written = benchmark.checkpoint_path(identity).read_text(encoding="utf-8")

    assert KEY_1 not in written and KEY_2 not in written
    assert "api_key" not in written
    redaction.clear_secrets()


def test_the_checkpoint_filename_survives_a_model_id_with_a_colon() -> None:
    """A colon makes an NTFS alternate data stream, which is invisible and uncommittable."""
    unsafe = "openrouter-nvidia/nemotron:free-abc123"

    safe = benchmark.safe_filename(unsafe)

    assert ":" not in safe and "/" not in safe
    assert safe == "openrouter-nvidia_nemotron_free-abc123"
