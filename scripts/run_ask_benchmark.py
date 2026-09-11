"""Run the frozen Ask VedaGraph benchmark, resumably, against the configured provider.

The question set in ``data/gold/ask_benchmark_v1.jsonl`` is **frozen**: it is the input
to this script, never an output of it. Questions are not edited in response to a poor
answer, because a benchmark that moves when the model stumbles measures nothing. The 28
questions carrying ``origin`` ``demo_v1``/``adversarial_v1`` are preserved verbatim from
the first live evaluation so runs remain comparable across providers.

**Resumable, because a free tier cannot answer 60 questions in one window.** Every
answered question is appended to a checkpoint file and flushed before the next one
starts, so a run stopped by an exhausted daily quota loses nothing. Re-running the same
command continues with only the unanswered questions.

**A resumed run is only valid if nothing moved between batches.** Provider, model,
question set, code commit and generation config are hashed into a run identity that is
written into the checkpoint and re-checked on every resume. Change any of them and this
script refuses to append, because merging two providers' answers into one score would
report a number that describes neither. Start a new run id instead.

**A momentary outage waits rather than ending the batch.** A free-tier gateway drops
requests for minutes at a time, and the adapter's retry ladder is sized for an HTTP
request -- seconds, because a live Ask call must not hang. A batch has the opposite
budget: nobody is waiting on question 34, so when the provider goes transiently dark
this script sleeps on a lengthening ladder and re-asks *the same* question, rather than
exiting and making a human notice and retype the command. The counter resets on every
answered question, so an hour of intermittent blips costs waiting, not attention.

What is never waited out is a fault that waiting cannot fix: a bad key, a blown context
window, a content filter, or a *daily* quota -- where each attempt is itself metered
against the allowance being waited for. Those stop the batch on the first occurrence.
The distinction is read from ``LLMError.retryable``, so this script still names no
provider.

Which provider answers is read from the environment alone -- ``VEDAGRAPH_LLM_PROVIDER``,
``VEDAGRAPH_LLM_MODEL``, ``VEDAGRAPH_LLM_API_KEY``. This script contains no provider
name and no per-provider branch, so a Gemini run and a Groq run execute identical code.

Usage::

    python scripts/run_ask_benchmark.py                 # start or resume
    python scripts/run_ask_benchmark.py --status        # what is left, answer nothing
    python scripts/run_ask_benchmark.py --pace 3.0
    python scripts/run_ask_benchmark.py --max-stalls 12 # ride out a longer outage
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vedagraph.api.ask.citation import classify_quotes, extract_cited_ids
from vedagraph.api.ask.models import AskRequest
from vedagraph.api.ask.service import AskService
from vedagraph.api.ask.synthesizer import SYSTEM_PROMPT
from vedagraph.api.config import get_api_settings
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.llm import get_llm_provider
from vedagraph.llm.base import LLMProvider, LLMRequest, LLMResponse
from vedagraph.llm.config import get_llm_settings
from vedagraph.llm.errors import LLMError, LLMProviderUnavailableError

BENCHMARK = Path("data/gold/ask_benchmark_v1.jsonl")
CHECKPOINT_DIR = Path("data/gold/ask_benchmark_runs")

#: Bumped only when the question set itself changes. A resumed run checks it.
BENCHMARK_VERSION = "ask_benchmark_v1"

#: Seconds between questions. Bulk runs are the one place provider pacing matters: the
#: free Gemini tier meters requests per minute and Groq meters tokens per minute, so an
#: unpaced 60-question run reports rate-limit failures that say nothing about the
#: pipeline. Interactive Ask is deliberately untouched by this -- it is a property of
#: this batch runner, not of the service.
DEFAULT_PACE_SECONDS = 3.0

#: Openings of the two answers the synthesizer returns when the *provider* failed rather
#: than the graph coming up empty. Both land on ``INSUFFICIENT_EVIDENCE``, so without
#: this check a backend outage would be scored as a correct refusal and a run that never
#: reached the model would report a clean sheet. Such a row is never checkpointed.
_DEGRADED_OPENINGS: tuple[str, ...] = (
    "The synthesis backend could not be reached",
    "The synthesis backend's content filter rejected",
)

#: Consecutive transient faults ridden out before the batch gives up on a question.
#: Reset by every answered question, so this bounds one outage rather than the run.
DEFAULT_MAX_STALLS = 5

#: First wait after a transient fault. Subsequent waits double.
DEFAULT_STALL_WAIT_SECONDS = 60.0

#: Ceiling on one wait. Past five minutes the ladder stops growing and simply repeats,
#: because a longer single sleep buys nothing a further attempt would not: the question
#: is whether the provider is back, and that is cheap to test.
_MAX_STALL_WAIT_SECONDS = 300.0


def _stall_seconds(base: float, stall: int) -> float:
    """Wait before re-asking, doubling per consecutive stall and capped."""
    return min(base * 2.0 ** (stall - 1), _MAX_STALL_WAIT_SECONDS)


def _waiting_can_help(fault: BaseException) -> bool:
    """Whether sleeping and asking again could plausibly clear this fault.

    Delegated entirely to ``LLMError.retryable`` so this script keeps no list of
    provider failure modes. That flag already carries the distinction that matters most
    to a batch: :class:`LLMRateLimitError` reports a *daily* allowance as non-retryable,
    because retrying one is not merely futile but metered -- each attempt spends the
    headroom the resumed batch needs. A per-minute limit, a 5xx and a timeout all stay
    retryable and are waited out here.
    """
    return isinstance(fault, LLMError) and fault.retryable


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _code_commit() -> str:
    """HEAD, marked dirty when *tracked* files differ from it.

    Untracked files are deliberately ignored, and that is load-bearing rather than
    lax. This script's own checkpoint lands in an untracked directory, so counting
    untracked files would mean the first batch ran at ``abc123`` and the second at
    ``abc123-dirty`` -- a different run identity, computed by the act of recording the
    first batch. The run would refuse to resume itself. Modifications to tracked files
    are what change the code under test, and those are still caught.

    Corollary: do not commit between batches of one run. Moving HEAD changes the
    identity, which is correct -- the code under test really did change -- but it means
    the remaining questions start a new run rather than continuing the old one.
    """
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{head}-dirty" if dirty else head
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass(frozen=True)
class RunIdentity:
    """Everything that must not move between batches of one benchmark run."""

    benchmark_version: str
    question_set_hash: str
    provider: str
    model: str
    code_commit: str
    config_hash: str

    @property
    def run_id(self) -> str:
        joined = "|".join(
            [
                self.benchmark_version,
                self.question_set_hash,
                self.provider,
                self.model,
                self.code_commit,
                self.config_hash,
            ]
        )
        return f"{self.provider}-{self.model.replace('/', '_')}-{_sha(joined)}"

    def as_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "benchmark_version": self.benchmark_version,
            "question_set_hash": self.question_set_hash,
            "provider": self.provider,
            "model": self.model,
            "code_commit": self.code_commit,
            "config_hash": self.config_hash,
        }


def build_identity(provider: LLMProvider, question_set_hash: str) -> RunIdentity:
    settings = get_llm_settings()
    # The generation knobs that change what the model writes, plus the system prompt.
    # Temperature moving between batches would make the halves incomparable.
    config = json.dumps(
        {
            "temperature": settings.vedagraph_llm_temperature,
            "max_output_tokens": settings.vedagraph_llm_max_output_tokens,
            "system_prompt": _sha(SYSTEM_PROMPT),
        },
        sort_keys=True,
    )
    return RunIdentity(
        benchmark_version=BENCHMARK_VERSION,
        question_set_hash=question_set_hash,
        provider=provider.name,
        model=provider.model,
        code_commit=_code_commit(),
        config_hash=_sha(config),
    )


class UsageRecordingProvider(LLMProvider):
    """Delegates to the real provider, remembering the last call's usage and fault.

    A wrapper rather than a new field on ``AskResponse``: token spend is a fact about
    this batch run, not part of the product's answer contract, and the application
    layers stay provider-agnostic because this only ever sees the normalised types.

    The fault is recorded for a sharper reason. The synthesizer deliberately converts a
    provider failure into a *degraded answer* rather than an exception, which is right
    for a live request -- one blip should not 500 a reader -- but it discards the cause,
    and the batch's whole stall policy turns on that cause. Catching it here, at the one
    seam that still sees the typed error, lets the runner tell a 5xx worth waiting out
    from a daily quota that is over, without the product layers growing a batch concern.
    """

    def __init__(self, inner: LLMProvider) -> None:
        self._inner = inner
        self.last_input_tokens: int | None = None
        self.last_output_tokens: int | None = None
        self.last_fault: BaseException | None = None

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model(self) -> str:
        return self._inner.model

    def clear_fault(self) -> None:
        """Forget the previous question's fault, so a stale one is never re-read."""
        self.last_fault = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            response = self._inner.generate(request)
        except BaseException as exc:
            self.last_fault = exc
            raise
        self.last_input_tokens = response.usage.input_tokens
        self.last_output_tokens = response.usage.output_tokens
        return response

    def stream(self, request: LLMRequest) -> Iterator[str]:
        return self._inner.stream(request)


def load_questions() -> tuple[list[dict[str, Any]], str]:
    raw = BENCHMARK.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return rows, _sha(raw)


#: Characters a run id may contain that a filename may not. Model ids carry several:
#: ``nvidia/nemotron-3-ultra-550b-a55b:free`` has both a slash and a colon.
_FILENAME_UNSAFE = re.compile(r'[:/\\<>"|?*]')


def safe_filename(run_id: str) -> str:
    """A filesystem-safe container name for a run id.

    Sanitising the *filename* only, never the run id itself: the id is the identity
    written into every row and compared on resume, and quietly rewriting it would make
    two different configurations look like one.

    The colon is why this exists and it fails silently on Windows rather than loudly.
    ``a55b:free-<hash>.jsonl`` is not a filename there -- it is an NTFS alternate data
    stream attached to a zero-byte file called ``a55b``. Writes appear to succeed, the
    bytes are readable back through the exact same path so resume still works, and the
    data is invisible to ``glob``, uncommittable by git, and lost by any ordinary copy.
    A benchmark that cannot be committed or graded is not a result.
    """
    return _FILENAME_UNSAFE.sub("_", run_id)


def checkpoint_path(identity: RunIdentity) -> Path:
    return CHECKPOINT_DIR / f"{safe_filename(identity.run_id)}.jsonl"


def load_checkpoint(identity: RunIdentity) -> dict[str, dict[str, Any]]:
    """Answers already recorded for this exact run identity, by question id.

    A checkpoint whose identity header disagrees is not this run and is never appended
    to -- the run id is derived from the identity, so a mismatch means a different file.
    """
    path = checkpoint_path(identity)
    if not path.exists():
        return {}
    done: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("run_id") != identity.run_id:
            raise SystemExit(
                f"Checkpoint {path} carries run_id {row.get('run_id')!r}, expected "
                f"{identity.run_id!r}. Results from different runs are never merged."
            )
        done[row["id"]] = row
    return done


def append_checkpoint(identity: RunIdentity, record: dict[str, Any]) -> None:
    """Append one answered question and flush, so a kill loses nothing."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = checkpoint_path(identity)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def _record(
    case: dict[str, Any],
    response: Any,
    identity: RunIdentity,
    usage: UsageRecordingProvider,
    elapsed_ms: float,
) -> dict[str, Any]:
    """Flatten one answered question, including the metrics the gates need."""
    packet_ids = {item.id for item in response.evidence}
    # Recomputed from the *returned* prose rather than trusted from the audit: this is
    # the number the gate is about. An id still readable in the answer that names nothing
    # in the packet is an invented citation that survived, whatever the audit reported.
    surviving = [cid for cid in extract_cited_ids(response.answer) if cid not in packet_ids]
    caveat_sources = [c.source for c in response.caveats]

    # Recomputed rather than counted off the caveat list. ``caveat_sources.count(
    # "quote_audit")`` is at most 1 per answer -- one caveat is raised however many runs
    # were flagged, and it names only the first three -- so a field called
    # "invalid_sanskrit_quotes" was reporting *answers carrying a flag*, not quotes. The
    # completed 60-question run recorded 32 under that name where the true run count was
    # 49. A gate metric must count the thing it is named after.
    by_id = {item.id: item for item in response.evidence}
    cited_items = [by_id[c.id] for c in response.citations if c.id in by_id]
    absent_runs, uncited_runs = classify_quotes(
        response.answer, cited_items, list(response.evidence)
    )
    return {
        **identity.as_dict(),
        "id": case["id"],
        "question_hash": _sha(case["question"] + json.dumps(case["context"], sort_keys=True)),
        "category": case["category"],
        "origin": case["origin"],
        "safety": case.get("safety"),
        "question": case["question"],
        "context": case["context"],
        "answered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "degraded": response.answer.startswith(_DEGRADED_OPENINGS),
        "answer": response.answer,
        "status": response.status.value,
        "support_level": response.support_level.value,
        "citation_ids": [c.id for c in response.citations],
        "citation_count": len(response.citations),
        "invented_citations_surviving": surviving,
        "evidence_count": len(response.evidence),
        "evidence_types": sorted({e.type.value for e in response.evidence}),
        "entities_resolved": response.retrieval_summary.entities_resolved,
        "entities_unresolved": response.retrieval_summary.entities_unresolved,
        "intents": response.retrieval_summary.intents,
        "channels_used": response.retrieval_summary.channels_used,
        "channels_empty": response.retrieval_summary.channels_empty,
        "interpretive": response.interpretive_content_present,
        "caveat_sources": caveat_sources,
        "caveats": [{"source": c.source, "text": c.text} for c in response.caveats],
        "invalid_citations_caught": caveat_sources.count("citation_audit"),
        "invalid_sanskrit_quotes": len(absent_runs),
        "unverified_sanskrit_runs": absent_runs,
        "uncited_sanskrit_runs": uncited_runs,
        "answers_flagged_for_quotes": caveat_sources.count("quote_audit"),
        "uncited_answer": "uncited_answer" in caveat_sources,
        # Read off the caveat list because that is the observable contract: these two
        # checks are *defined* by what they tell the reader, and a boolean recorded from
        # anywhere else could disagree with the answer that shipped.
        "generation_truncated": "generation_truncated" in caveat_sources,
        "quantitative_flagged": "quantitative_audit" in caveat_sources,
        "input_tokens": usage.last_input_tokens,
        "output_tokens": usage.last_output_tokens,
        "latency_ms": round(elapsed_ms, 1),
        "total_ms": response.retrieval_summary.total_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pace", type=float, default=DEFAULT_PACE_SECONDS)
    parser.add_argument("--status", action="store_true", help="Report progress and answer nothing.")
    parser.add_argument(
        "--limit", type=int, default=None, help="Answer at most N unanswered questions."
    )
    parser.add_argument(
        "--max-stalls",
        type=int,
        default=DEFAULT_MAX_STALLS,
        help=(
            "Consecutive transient provider faults to ride out before stopping. "
            "Reset by every answered question. 0 restores fail-fast."
        ),
    )
    parser.add_argument(
        "--stall-wait",
        type=float,
        default=DEFAULT_STALL_WAIT_SECONDS,
        help="Seconds to wait after the first transient fault. Doubles, capped at 300.",
    )
    args = parser.parse_args()

    logging.disable(logging.WARNING)
    cases, question_set_hash = load_questions()

    provider = UsageRecordingProvider(get_llm_provider())
    identity = build_identity(provider, question_set_hash)
    done = load_checkpoint(identity)
    remaining = [c for c in cases if c["id"] not in done]

    print(f"run_id      {identity.run_id}")
    print(f"provider    {identity.provider}  model {identity.model}")
    print(f"commit      {identity.code_commit}   questions {len(cases)}")
    print(f"checkpoint  {checkpoint_path(identity)}")
    print(f"answered    {len(done)}/{len(cases)}   remaining {len(remaining)}\n")

    if args.status:
        return
    if not remaining:
        print("Benchmark complete. Nothing to resume.")
        return
    if args.limit:
        remaining = remaining[: args.limit]

    repo = Neo4jRepository(get_api_settings())
    service = AskService(repo, provider)
    answered = 0
    index = 0
    stalls = 0
    # Nothing to pace against before the first question, and a stall wait has already
    # paced the retry that follows it far past anything --pace would add.
    skip_pace = True
    try:
        while index < len(remaining):
            case = remaining[index]
            if not skip_pace:
                time.sleep(args.pace)
            skip_pace = False

            provider.clear_fault()
            started = time.monotonic()
            fault: BaseException | None = None
            record: dict[str, Any] | None = None
            try:
                response = service.ask(AskRequest(question=case["question"], **case["context"]))
            except LLMError as exc:
                # Reached the runner un-degraded: an auth or configuration fault the
                # synthesizer re-raises rather than answering around.
                fault = exc
            except Exception as exc:
                print(f"[{case['id']}] ERROR {type(exc).__name__}: {str(exc)[:120]}")
                index += 1
                continue
            else:
                record = _record(
                    case, response, identity, provider, (time.monotonic() - started) * 1000
                )
                if record["degraded"]:
                    # The provider, not the pipeline, failed. Never checkpointed: a
                    # degraded row scored as a correct refusal would flatter the run, and
                    # on resume it would never be retried. The cause is not in the
                    # response -- the synthesizer swallowed it -- so read it off the
                    # wrapper that saw it thrown. The fallback is not decoration: a
                    # degraded answer this script cannot attribute is still the backend
                    # failing to answer, and inferring nothing would either crash the
                    # batch or, worse, let an unattributed degradation look like success.
                    fault = provider.last_fault or LLMProviderUnavailableError(
                        provider=provider.name
                    )
                    record = None

            if fault is not None:
                detail = getattr(fault, "detail", str(fault)) or type(fault).__name__
                if not _waiting_can_help(fault):
                    print(f"\nSTOPPING at {case['id']}: {type(fault).__name__}")
                    print(f"  {detail}")
                    print(f"  {len(done) + answered}/{len(cases)} answered and checkpointed.")
                    print("  Waiting will not clear this. Re-run once it is resolved.")
                    return
                stalls += 1
                if stalls > args.max_stalls:
                    print(f"\nSTOPPING at {case['id']}: still failing after {args.max_stalls}")
                    print(f"  consecutive waits. Last fault: {detail}")
                    print(f"  {len(done) + answered}/{len(cases)} answered and checkpointed.")
                    print("  Re-run this command when the provider recovers.")
                    return
                wait = _stall_seconds(args.stall_wait, stalls)
                resume_at = time.strftime("%H:%M:%S", time.localtime(time.time() + wait))
                print(
                    f"   .. {case['id']} {type(fault).__name__}: waiting {wait:.0f}s "
                    f"(stall {stalls}/{args.max_stalls}, retry at {resume_at})",
                    flush=True,
                )
                time.sleep(wait)
                skip_pace = True
                continue

            assert record is not None  # no fault means _record ran
            append_checkpoint(identity, record)
            answered += 1
            index += 1
            # An answered question means the provider is back; the next outage starts
            # its ladder from the bottom rather than inheriting an old one's impatience.
            stalls = 0
            print(
                f"[{len(done) + answered:>2}/{len(cases)}] {record['status']:<22}"
                f" cites={record['citation_count']:<2}"
                f" tok={record['input_tokens'] or 0:>5}/{record['output_tokens'] or 0:<4}"
                f" {record['latency_ms']:>6.0f}ms  {case['question'][:42]}",
                flush=True,
            )
    except KeyboardInterrupt:
        # Ctrl-C during a multi-minute stall wait is the expected way to abandon a batch.
        # Every answered question is already flushed, so this loses nothing and should
        # read as a clean exit rather than a traceback.
        print(f"\nInterrupted. {len(done) + answered}/{len(cases)} answered and checkpointed.")
        print("  Re-run this command to continue.")
        return
    finally:
        repo.close()

    total = len(done) + answered
    print(f"\n{total}/{len(cases)} answered -> {checkpoint_path(identity)}")
    if total < len(cases):
        print("Re-run this command to continue the remaining questions.")


if __name__ == "__main__":
    main()
