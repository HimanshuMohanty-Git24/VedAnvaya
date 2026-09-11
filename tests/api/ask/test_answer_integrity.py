"""What the assembled pipeline refuses to present as a finished, faithful answer.

The pieces are unit-tested next door -- the validator in ``test_quantitative.py``, the
finish-reason table in ``tests/llm/test_provider_contract.py``, the repair retry in
``test_synthesis_contract.py``. What is asserted here is the wiring: that both checks
actually reach :class:`AskService`'s grading and caveats, because a guardrail that
computes a correct verdict and does not change the response is decoration.

Two defects are pinned, both observed in the frozen 60-question benchmark:

- an answer whose only quantitative sentence contradicted the rows it cited was returned
  ``SUPPORTED`` / ``STRONG`` with no caveat;
- four answers stopped at the output cap and every one of them was presented as complete.

The graph is the scripted :class:`FakeRepository` and the provider is a stub, so nothing
here needs a database, a key or a socket.
"""

from __future__ import annotations

from typing import Any

from tests.api.conftest import FakeRepository
from vedagraph.api.ask.models import (
    AskRequest,
    AskResponse,
    EvidenceItemType,
    SupportLevel,
)
from vedagraph.api.ask.service import AskService
from vedagraph.api.models.common import KnowledgeStatus
from vedagraph.llm.base import LLMProvider, LLMRequest, LLMResponse, LLMUsage


class StubProvider(LLMProvider):
    def __init__(self, *texts: str, finish_reason: str = "stop") -> None:
        self._texts = list(texts)
        self._finish_reason = finish_reason
        self.calls = 0

    @property
    def name(self) -> str:
        return "stub"

    @property
    def model(self) -> str:
        return "stub-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        text = self._texts[min(self.calls - 1, len(self._texts) - 1)]
        return LLMResponse(
            text=text,
            finish_reason=self._finish_reason,
            provider="stub",
            model="stub-1",
            usage=LLMUsage(input_tokens=10, output_tokens=5),
        )


def _passage(n: int) -> dict[str, Any]:
    return {
        "canonical_key": f"VG:RV:SAK:M01:S001:V00{n}",
        "canonical_citation": f"RV 1.1.{n}",
        "veda": "RV",
        "display_type": "MANTRA",
        "sanskrit": f"agnim ile purohitam {n}",
        "translation": "I laud Agni, the chosen Priest.",
        "translator": "Griffith",
        "relation_type": "MENTIONS_ENTITY",
    }


#: One resolved Devata, as the batched resolver returns it.
AGNI_ROW: dict[str, Any] = {
    "asked": "Agni",
    "rung": 0,
    "entity_key": "VG:DEVATA:AGNIH",
    "label": "Agni",
    "entity_type": "Devata",
    "description": "The sacrificial fire.",
    "match_rank": 0,
}

#: Per-corpus counts whose smallest figure is far below a hundred -- the shape of the row
#: the Q60 answer cited while calling every corpus "hundreds".
BY_VEDA_ROWS: list[dict[str, Any]] = [
    {
        "veda": veda,
        "relation_type": "MENTIONS_ENTITY",
        "certain": count,
        "probable": 0,
        "ambiguous": 0,
        "ungraded": 0,
        "total": count,
    }
    for veda, count in (("AV", 18), ("RV", 195), ("SV", 38), ("YV", 49))
]


def three_passage_repo() -> FakeRepository:
    """Enough substantive evidence for a well-cited answer to grade SUPPORTED/STRONG.

    Driven through passage lookup rather than an entity profile, so the packet holds
    three PASSAGE items and nothing that carries a figure.
    """
    return FakeRepository({"MATCH (p:Passage)": [_passage(1), _passage(2), _passage(3)]})


def counted_repo() -> FakeRepository:
    """A resolvable entity whose per-corpus distribution is the packet's only figures."""
    return FakeRepository(
        {
            "UNWIND $candidates AS candidate": [AGNI_ROW],
            "AS certain": BY_VEDA_ROWS,
            "MATCH (p:Passage)-[r]->": [_passage(1), _passage(2), _passage(3)],
        }
    )


def ask(repo: FakeRepository, provider: LLMProvider, question: str) -> AskResponse:
    return AskService(repo, provider).ask(AskRequest(question=question))


def sources(response: AskResponse) -> list[str]:
    return [caveat.source for caveat in response.caveats]


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

CITED_ANSWER = "Agni is the invoked priest [E1], [E2] and the offerer [E3]."


def test_an_untruncated_answer_keeps_its_grade_and_gains_no_caveat() -> None:
    response = ask(three_passage_repo(), StubProvider(CITED_ANSWER), "What does RV 1.1.1 contain?")

    assert response.status is KnowledgeStatus.SUPPORTED
    assert response.support_level is SupportLevel.STRONG
    assert "generation_truncated" not in sources(response)


def test_a_truncated_answer_cannot_stay_supported() -> None:
    """The defect: four capped benchmark answers were all returned as complete."""
    provider = StubProvider(CITED_ANSWER, finish_reason="length")

    response = ask(three_passage_repo(), provider, "What does RV 1.1.1 contain?")

    assert response.status is KnowledgeStatus.PARTIAL
    assert response.support_level is SupportLevel.LIMITED


def test_a_truncated_answer_carries_a_plain_caveat() -> None:
    provider = StubProvider(CITED_ANSWER, finish_reason="length")

    response = ask(three_passage_repo(), provider, "What does RV 1.1.1 contain?")

    caveat = next(c for c in response.caveats if c.source == "generation_truncated")
    assert "reached its output limit" in caveat.text
    assert "evidence remains available" in caveat.text


def test_the_truncation_caveat_exposes_no_provider_jargon() -> None:
    provider = StubProvider(CITED_ANSWER, finish_reason="length")

    response = ask(three_passage_repo(), provider, "What does RV 1.1.1 contain?")

    caveat = next(c for c in response.caveats if c.source == "generation_truncated")
    lowered = caveat.text.lower()
    for jargon in ("finish_reason", "max_tokens", "token", "length", "stop_reason"):
        assert jargon not in lowered


def test_a_truncated_answer_keeps_its_evidence_reachable() -> None:
    """The prose is a fragment; the packet behind it is not, and stays readable."""
    provider = StubProvider(CITED_ANSWER, finish_reason="length")

    response = ask(three_passage_repo(), provider, "What does RV 1.1.1 contain?")

    assert len(response.evidence) == 3
    assert [c.id for c in response.citations] == ["E1", "E2", "E3"]


# ---------------------------------------------------------------------------
# Quantitative
# ---------------------------------------------------------------------------


def distribution_id(repo: FakeRepository) -> str:
    """The packet id of the per-corpus row, found by type rather than by position.

    Hard-coding "E4" would make these tests fail whenever an unrelated channel changed
    how many items precede the distribution -- a brittleness that says nothing about the
    contract under test.
    """
    probe = ask(repo, StubProvider("no citations here"), "Where is Agni attested?")
    return next(
        item.id for item in probe.evidence if item.type is EvidenceItemType.CORPUS_DISTRIBUTION
    )


def overstated(eid: str) -> str:
    return (
        f"Agni is the invoked priest [E1], [E2] and the offerer [E3]. "
        f"It appears in hundreds of verses in each corpus [{eid}]."
    )


def accurate(eid: str) -> str:
    return (
        f"Agni is the invoked priest [E1], [E2] and the offerer [E3]. "
        f"It appears in 18 AV, 195 RV, 38 SV and 49 YV verses [{eid}]."
    )


def test_the_counted_packet_is_shaped_as_the_test_assumes() -> None:
    """Guards the fixture itself: without the distribution row the rest proves nothing."""
    repo = counted_repo()
    eid = distribution_id(repo)

    response = ask(repo, StubProvider(accurate(eid)), "Where is Agni attested?")

    item = next(i for i in response.evidence if i.id == eid)
    assert "18 verses" in (item.fact or "")
    assert response.status is KnowledgeStatus.SUPPORTED


def test_an_answer_contradicting_its_own_figures_cannot_stay_supported() -> None:
    """The Q60 defect, at the level a client sees.

    Both drafts overstate, so the single repair retry is spent and the finding stands.
    """
    repo = counted_repo()
    draft = overstated(distribution_id(repo))
    provider = StubProvider(draft, draft)

    response = ask(repo, provider, "Where is Agni attested?")

    assert provider.calls == 2, "one repair retry, not a loop"
    assert response.status is not KnowledgeStatus.SUPPORTED
    assert "quantitative_audit" in sources(response)


def test_the_quantitative_caveat_is_written_for_a_reader() -> None:
    repo = counted_repo()
    draft = overstated(distribution_id(repo))

    response = ask(repo, StubProvider(draft, draft), "Where is Agni attested?")

    caveat = next(c for c in response.caveats if c.source == "quantitative_audit")
    assert "could not be verified" in caveat.text
    # No rule names and no evidence ids: a caveat is for the reader, not the maintainer.
    assert "UNIVERSAL" not in caveat.text
    assert "[E" not in caveat.text


def test_a_repaired_answer_is_returned_clean() -> None:
    """A first draft that fails and a rewrite that passes must grade as a good answer."""
    repo = counted_repo()
    eid = distribution_id(repo)
    provider = StubProvider(overstated(eid), accurate(eid))

    response = ask(repo, provider, "Where is Agni attested?")

    assert provider.calls == 2
    assert response.answer == accurate(eid)
    assert response.status is KnowledgeStatus.SUPPORTED
    assert "quantitative_audit" not in sources(response)


def test_an_accurate_answer_is_never_retried_or_flagged() -> None:
    repo = counted_repo()
    provider = StubProvider(accurate(distribution_id(repo)))

    response = ask(repo, provider, "Where is Agni attested?")

    assert provider.calls == 1
    assert "quantitative_audit" not in sources(response)


def test_a_downgrade_never_raises_an_already_weak_grade() -> None:
    """An uncited answer is INSUFFICIENT. Truncating it must not promote it to LIMITED."""
    provider = StubProvider("Agni is a deity.", finish_reason="length")

    response = ask(three_passage_repo(), provider, "What does RV 1.1.1 contain?")

    assert response.status is KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert response.support_level is SupportLevel.INSUFFICIENT
