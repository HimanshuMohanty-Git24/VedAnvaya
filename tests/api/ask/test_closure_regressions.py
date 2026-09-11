"""The defects found by live evaluation, pinned so a rewrite cannot reintroduce them.

Each test here names a failure that was observed against the real graph or a real
provider, not a hypothetical. They are collected in one file because they are the
Product V1 acceptance regressions: if this file passes, the seven bugs closed during the
build are still closed.

Unit-level by construction -- none of these needs a live provider or a live database,
so the acceptance surface stays runnable in CI where neither exists.
"""

from __future__ import annotations

import pathlib

import pytest

from vedagraph.api.ask.citation import audit, extract_cited_ids
from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.matching import token_match
from vedagraph.api.ask.models import EvidenceItem, EvidenceItemType
from vedagraph.api.ask.planner import plan
from vedagraph.api.ask.resolver import _ALIAS_PROPS, _LABEL_PROPS
from vedagraph.llm.base import LLMMessage, LLMRequest
from vedagraph.llm.providers.gemini import _is_exhausted_for_the_day
from vedagraph.llm.providers.openai_compat import (
    _is_exhausted_for_the_day as _compat_exhausted,
)


def _packet(*ids: str) -> EvidencePacket:
    return EvidencePacket(
        items=[
            EvidenceItem(
                id=i,
                type=EvidenceItemType.PASSAGE,
                citation=f"RV 1.1.{n}",
                sanskrit="agním īḷe puróhitaṃ",
            )
            for n, i in enumerate(ids, start=1)
        ]
    )


# -- 1. the resolver reads real identity properties -------------------------------


def test_resolver_never_reads_a_generic_label_property() -> None:
    """There is no `label` property in this graph.

    A resolver written against the obvious guess resolved nothing at all, and the
    response said "no evidence" -- which reads as a fact about the corpus rather than
    about the query. Every property named here is one this graph actually carries.
    """
    every = set(_LABEL_PROPS) | set(_ALIAS_PROPS)
    assert "n.label" not in every
    assert "n.name" not in every
    # display_label is the only universal one and must stay in the set.
    assert "n.display_label" in _LABEL_PROPS
    assert every, "the resolver must enumerate identity properties explicitly"


# -- 2 & 3. word-boundary containment ---------------------------------------------


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("rta", "mortar (ulūkhala)"),  # the mortar is not cosmic order
        ("ap", "appear"),  # the waters are not the verb
        ("ap", "apacit swellings (apacit)"),  # nor a substring of a disease name
    ],
)
def test_a_name_does_not_match_inside_a_longer_word(name: str, label: str) -> None:
    assert token_match(name, label) is False


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("rta", "cosmic order (ṛta)"),
        ("ap", "waters (ap)"),
        ("takman", "fever (takman)"),
    ],
)
def test_a_whole_token_still_matches(name: str, label: str) -> None:
    assert token_match(name, label) is True


# -- 4. lowercase concepts are nominated ------------------------------------------


@pytest.mark.parametrize("term", ["fever", "ayas", "rakshas", "krimi"])
def test_a_lowercase_meaningful_term_is_nominated(term: str) -> None:
    """Restricting nomination to capitalised words made "fever" retrieve nothing.

    The resolver can reach VG:CONCEPT:TAKMAN-FEVER from the word perfectly well; the
    planner simply never offered it. An empty packet is what a model answers from
    memory, so this gap produced ungrounded prose rather than a visible failure.
    """
    result = plan(f"What does the Atharvaveda say about {term}?")
    nominated = {c.lower() for c in result.entities_mentioned}
    assert term in nominated, f"{term!r} not nominated; got {sorted(nominated)}"


# -- 5. grouped citations validate every id ---------------------------------------


def test_every_id_in_a_grouped_citation_is_extracted() -> None:
    assert extract_cited_ids("shown in [E6, E7, E8, E9].") == ["E6", "E7", "E8", "E9"]


def test_an_invented_id_inside_a_group_is_removed_from_the_prose() -> None:
    """A group-blind rewrite left the fabricated id in the sentence.

    The caveat then claimed it had been removed, which is worse than not checking.
    """
    result = audit("Supported by [E1, E2, E99].", _packet("E1", "E2"))
    assert result.invented_ids == ["E99"]
    assert "E99" not in result.cleaned_answer
    assert "E1" in result.cleaned_answer and "E2" in result.cleaned_answer


# -- 6. fullwidth citation markers stay recognised ---------------------------------


def test_fullwidth_markers_are_recognised_and_normalised_to_ascii() -> None:
    """gpt-oss-120b on Groq emits 【E1】.

    Unrecognised, a correctly grounded answer was graded INSUFFICIENT_EVIDENCE with an
    empty citation list -- telling the reader the graph had nothing to say. Recognised
    but not normalised, the marker reached the page as inert literal text, because the
    frontend builds its clickable chips by parsing ASCII [E1].
    """
    assert extract_cited_ids("as stated 【E1】") == ["E1"]
    result = audit("as stated 【E1】", _packet("E1"))
    assert [c.id for c in result.citations] == ["E1"]
    assert "[E1]" in result.cleaned_answer
    assert "【" not in result.cleaned_answer


# -- 7. an exhausted daily quota is not retried ------------------------------------


def test_a_per_day_quota_is_distinguished_from_a_per_minute_one() -> None:
    """Retrying the wrong 429 spends tomorrow's allowance proving today's is gone."""
    per_day = {
        "error": {"details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProject"}]}]}
    }
    per_minute = {
        "error": {"details": [{"violations": [{"quotaId": "GenerateRequestsPerMinutePerProject"}]}]}
    }
    assert _is_exhausted_for_the_day(per_day) is True
    assert _is_exhausted_for_the_day(per_minute) is False


@pytest.mark.parametrize("body", [None, {}, {"error": {}}, {"error": {"details": "nope"}}, "text"])
def test_an_unparseable_quota_body_is_not_read_as_a_daily_limit(body: object) -> None:
    """Absence of the marker must not be read as presence of a daily ceiling.

    Guessing "daily" from a malformed body would turn a momentary spike into a run-ending
    failure, which is the opposite error and just as expensive.
    """
    assert _is_exhausted_for_the_day(body) is False


# -- ASK_BL_03. citation ranges cannot produce a false validation ------------------


def test_a_citation_range_never_smuggles_an_unvalidated_middle_id() -> None:
    """`[E1-E4]` is not supported, and that is safe rather than merely unimplemented.

    The endpoints are the only ids extracted, so E2 and E3 are never validated -- and
    because every surviving group is rewritten to the ids that *were* validated, they
    are also erased from the prose. The reader is left with exactly the citations the
    audit checked. Support for the range spelling remains ASK_BL_03; what is pinned here
    is that its absence cannot fabricate a link.
    """
    packet = _packet("E1", "E4")  # E2 and E3 deliberately absent from the packet
    result = audit("See [E1-E4].", packet)

    assert result.invented_ids == []
    # The unvalidated middle is gone from the prose, not merely unlinked.
    assert "E2" not in result.cleaned_answer
    assert "E3" not in result.cleaned_answer
    assert result.cleaned_answer == "See [E1, E4]."
    assert {c.id for c in result.citations} == {"E1", "E4"}


def test_a_range_whose_endpoint_is_invented_is_still_caught() -> None:
    result = audit("See [E1-E9].", _packet("E1"))
    assert result.invented_ids == ["E9"]
    assert "E9" not in result.cleaned_answer


# -- 7b. the same quota guard on the OpenAI-compatible path ------------------------


@pytest.mark.parametrize(
    "message",
    [
        # Groq, verbatim from the benchmark run that found this.
        "Rate limit reached for model `openai/gpt-oss-120b` in organization `org_x` "
        "service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199681",
        "You exceeded your current quota: requests per day (RPD)",
        "Daily limit reached for this model.",
    ],
)
def test_a_daily_ceiling_is_recognised_on_the_openai_compatible_path(message: str) -> None:
    assert _compat_exhausted(Exception(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        "Rate limit reached on tokens per minute (TPM): Limit 6000",
        "Rate limit reached for requests per minute (RPM).",
        "429 Too Many Requests",
        "",
    ],
)
def test_a_per_minute_limit_is_still_retried(message: str) -> None:
    """Misreading a transient spike as a daily ceiling ends a run that would recover."""
    assert _compat_exhausted(Exception(message)) is False


# -- attribution vs mention: never merged into one unlabelled number ---------------


def test_a_corpus_distribution_labels_the_relationship_behind_every_count() -> None:
    """The channel returns one row per (veda, relation_type).

    Joined without labels, the fact read "AV: 68 verses; AV: 68 verses; AV: 66 verses" --
    one corpus apparently counted three times, summing to 202 verses in a corpus that has
    68. And the figures being merged were precisely the distinction this API may never
    blur: PROTECTS_FROM, MENTIONS_ENTITY and ABOUT_CONCEPT are three different claims.
    The item also named only the *first* row's relation, asserting a relationship it had
    not measured.
    """
    from vedagraph.api.ask.evidence import build_evidence_packet
    from vedagraph.api.ask.retriever import RetrievalResult

    rows = [
        {
            "veda": "AV",
            "relation_type": "PROTECTS_FROM",
            "ungraded": 68,
            "_entity_key": "K",
            "_entity_label": "demon (rakṣas)",
        },
        {
            "veda": "AV",
            "relation_type": "MENTIONS_ENTITY",
            "ungraded": 68,
            "_entity_key": "K",
            "_entity_label": "demon (rakṣas)",
        },
        {
            "veda": "AV",
            "relation_type": "ABOUT_CONCEPT",
            "ungraded": 66,
            "_entity_key": "K",
            "_entity_label": "demon (rakṣas)",
        },
    ]
    packet = build_evidence_packet(RetrievalResult(entity_by_veda=rows))
    item = next(i for i in packet.items if i.type is EvidenceItemType.CORPUS_DISTRIBUTION)

    assert item.fact is not None
    for relation in ("PROTECTS_FROM", "MENTIONS_ENTITY", "ABOUT_CONCEPT"):
        assert relation in item.fact, f"{relation} count is unlabelled"
        assert relation in (item.relationship_type or "")
    # No bare repeated "AV: n verses" that a reader could only read as one measurement.
    assert "AV: 68 verses; AV: 68 verses" not in item.fact
    assert item.qualifier is not None and "must not be added" in item.qualifier


# -- a transient empty completion must not end a batch ----------------------------


def test_an_empty_choices_response_is_retryable_not_permanent() -> None:
    """A 200 carrying no choice is the upstream failing behind the gateway.

    OpenRouter returned one on the fifth question of a 60-question benchmark and the
    adapter classified it as a permanent LLMResponseError, ending the batch -- while the
    very next call to the same model succeeded. It is now raised as unavailable so the
    existing retry ladder applies.
    """
    from types import SimpleNamespace

    from vedagraph.llm.errors import LLMProviderUnavailableError, LLMResponseError
    from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

    provider = OpenAICompatProvider(
        provider_name="openrouter", api_key="k", model="m", max_retries=0
    )

    class _Client:
        def __init__(self) -> None:
            self.calls = 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, **_: object) -> SimpleNamespace:
            self.calls += 1
            return SimpleNamespace(choices=[], usage=None, id="x", model="m")

    provider._client = _Client()  # type: ignore[assignment]

    with pytest.raises(LLMProviderUnavailableError) as caught:
        provider.generate(LLMRequest(messages=[LLMMessage(role="user", content="hi")]))
    assert caught.value.retryable is True
    # And specifically not the permanent classification that stopped the run.
    assert not isinstance(caught.value, LLMResponseError)


# -- a run id is not always a legal filename --------------------------------------


@pytest.mark.parametrize(
    "run_id",
    [
        "openrouter-nvidia_nemotron-3-ultra-550b-a55b:free-2845e1ab",
        "openai_compatible-vendor/model:tag-abc123",
    ],
)
def test_a_checkpoint_filename_carries_no_path_metacharacters(run_id: str) -> None:
    """The colon fails silently on Windows, which is why it needs a test.

    ``a55b:free-<hash>.jsonl`` is not a file there, it is an NTFS alternate data stream
    on a zero-byte file named ``a55b``. Writes succeed, reads through the identical path
    succeed, so resume still works -- and the data is invisible to glob, uncommittable,
    and destroyed by any ordinary copy. A benchmark that cannot be committed is not a
    result.
    """
    # scripts/ is not a package, so the module is loaded by path.
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "_bench", pathlib.Path(__file__).parents[3] / "scripts" / "run_ask_benchmark.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_bench"] = module
    spec.loader.exec_module(module)
    safe_filename = module.safe_filename

    name = safe_filename(run_id)
    assert not set(name) & set(r':/\<>"|?*'), name
    # Still distinguishes runs that differ only in the sanitised characters.
    assert safe_filename("a:b") != safe_filename("a:c")


# -- a momentary outage must not cost a human a retyped command -------------------


def _bench_module() -> object:
    """Load the benchmark runner by path; scripts/ is not a package."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "_bench", pathlib.Path(__file__).parents[3] / "scripts" / "run_ask_benchmark.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_bench"] = module
    spec.loader.exec_module(module)
    return module


def test_a_transient_fault_is_waited_out_and_a_daily_one_is_not() -> None:
    """The batch's stall policy must read the distinction, not guess at it.

    Observed twice on one resume: OpenRouter's free tier returned an empty 200, the run
    stopped, and a human had to notice and retype the command. Waiting is the right
    answer there. It is the wrong answer to an exhausted daily allowance, where every
    probe is metered against the headroom being waited for -- so the two must not be
    conflated into "the provider errored".
    """
    from vedagraph.llm.errors import (
        LLMAuthenticationError,
        LLMContentBlockedError,
        LLMProviderUnavailableError,
        LLMRateLimitError,
        LLMTimeoutError,
    )

    waiting_can_help = _bench_module()._waiting_can_help  # type: ignore[attr-defined]

    assert waiting_can_help(LLMProviderUnavailableError(provider="openrouter"))
    assert waiting_can_help(LLMTimeoutError(provider="openrouter", timeout_seconds=60))
    assert waiting_can_help(LLMRateLimitError(provider="openrouter"))

    assert not waiting_can_help(LLMRateLimitError(provider="openrouter", daily_exhausted=True)), (
        "a daily allowance does not refill while a batch sleeps"
    )
    assert not waiting_can_help(LLMAuthenticationError(provider="openrouter"))
    assert not waiting_can_help(LLMContentBlockedError(provider="openrouter"))


def test_the_stall_ladder_grows_and_then_stops_growing() -> None:
    """Doubling rides out a longer outage; the cap keeps the probe cheap.

    Past five minutes a longer single sleep buys nothing another attempt would not --
    the only question is whether the provider is back, and asking is cheap.
    """
    module = _bench_module()
    stall_seconds = module._stall_seconds  # type: ignore[attr-defined]
    cap = module._MAX_STALL_WAIT_SECONDS  # type: ignore[attr-defined]

    assert stall_seconds(60.0, 1) == 60.0
    assert stall_seconds(60.0, 2) == 120.0
    assert stall_seconds(60.0, 3) == 240.0
    assert stall_seconds(60.0, 4) == cap
    assert stall_seconds(60.0, 99) == cap


def test_the_wrapper_keeps_the_fault_the_synthesizer_swallows() -> None:
    """Without this the runner cannot tell *why* an answer came back degraded.

    Degrading rather than raising is correct for a live request -- one provider blip
    should not 500 a reader -- but it discards the cause, and the whole stall policy
    turns on the cause. The wrapper is the last seam that still sees the typed error.
    """
    from vedagraph.llm.base import LLMProvider, LLMResponse, LLMUsage
    from vedagraph.llm.errors import LLMProviderUnavailableError

    module = _bench_module()

    class _Blip(LLMProvider):
        def __init__(self) -> None:
            self.fail = True

        @property
        def name(self) -> str:
            return "openrouter"

        @property
        def model(self) -> str:
            return "free-model"

        def generate(self, request: LLMRequest) -> LLMResponse:
            if self.fail:
                raise LLMProviderUnavailableError(provider="openrouter")
            return LLMResponse(
                text="ok",
                finish_reason="stop",
                provider="openrouter",
                model="free-model",
                usage=LLMUsage(input_tokens=5, output_tokens=2),
            )

        def stream(self, request: LLMRequest):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    inner = _Blip()
    wrapped = module.UsageRecordingProvider(inner)  # type: ignore[attr-defined]
    req = LLMRequest(messages=[LLMMessage(role="user", content="q")])

    with pytest.raises(LLMProviderUnavailableError):
        wrapped.generate(req)
    assert isinstance(wrapped.last_fault, LLMProviderUnavailableError)

    # And a stale fault is never re-read against the next question.
    wrapped.clear_fault()
    inner.fail = False
    wrapped.generate(req)
    assert wrapped.last_fault is None
    assert wrapped.last_input_tokens == 5


# -- benchmark closure: the Samavedic locus that was denied out of existence ----------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # The defect: every Samavedic citation carries a section token, and the pattern
        # expected digits straight after the Veda code. All 1,844 Samavedic mantras were
        # unreachable by passage lookup, so "What does SV ARANYA 1.1 contain?" retrieved
        # nothing and was answered "VedaGraph does not contain any Aranyaka texts" about a
        # passage the graph stores.
        ("What does SV ARANYA 1.1 contain?", "SV ARANYA 1.1"),
        ("Tell me about SV UTTARA 9.2.10.1", "SV UTTARA 9.2.10.1"),
        ("SV CHANDA 1.1", "SV CHANDA 1.1"),
        ("sv mahanamnya 1.2 please", "SV MAHANAMNYA 1.2"),
        # Unsectioned loci must keep parsing exactly as before.
        ("What does RV 10.129.1 say?", "RV 10.129.1"),
        ("Summarise AVS 1.1.1.", "AVS 1.1.1"),
        ("What is VSM 1.1 about?", "VSM 1.1"),
    ],
)
def test_sectioned_samavedic_locus_is_a_passage_key(question: str, expected: str) -> None:
    assert plan(question).passage_key == expected


def test_a_bare_veda_and_number_is_still_not_a_locus() -> None:
    """Two numeric parts remain the minimum, so widening the pattern cannot over-match."""
    assert plan("Which Veda has the most mentions of Indra?").passage_key is None
    assert plan("Does the Samaveda mention Varuna?").passage_key is None
    assert plan("What is in RV 10?").passage_key is None


def test_scope_does_not_deny_the_arcika_section_it_cites() -> None:
    """ "Aranyaka" names a genre this graph lacks *and* a section it holds.

    Stated only as "contains NO Aranyaka", the scope line licensed a refusal of
    ``SV ARANYA 1.1``. Both senses must be named for the true statement about the genre
    not to be read as a false one about the section.
    """
    from vedagraph.api.ask.synthesizer import SYSTEM_PROMPT

    assert "Aranyaka-genre text" in SYSTEM_PROMPT
    assert "SV ARANYA locus is arcika verse text that IS in this corpus" in SYSTEM_PROMPT
