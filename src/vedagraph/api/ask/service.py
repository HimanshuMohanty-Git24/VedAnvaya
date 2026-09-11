"""The Ask pipeline, assembled.

    question
      -> plan          deterministic, no model
      -> resolve       names become graph nodes, or stay names
      -> retrieve      named Cypher over selected channels
      -> freeze        the evidence packet closes here
      -> synthesise    the only step that touches a provider
      -> audit         every citation checked against the packet
      -> respond

Everything above ``synthesise`` is provider-independent and would produce byte-identical
evidence under any configured vendor. That is the architectural claim this module exists
to make true: the provider is a parameter of one step, not a property of the pipeline.

**Caveats are derived, not written.** Each one is built from something measured during
this request -- a channel that returned nothing, a corpus with no searchable surface, a
citation that failed its check. Prose typed once and never re-checked drifts from the data
it describes, and this project has shipped that defect before.
"""

from __future__ import annotations

import logging
import time
from typing import Final

from vedagraph.api.ask import citation as citation_stage
from vedagraph.api.ask import evidence as evidence_stage
from vedagraph.api.ask import planner as planner_stage
from vedagraph.api.ask import resolver as resolver_stage
from vedagraph.api.ask import retriever as retriever_stage
from vedagraph.api.ask import synthesizer as synthesis_stage
from vedagraph.api.ask.models import (
    AskRequest,
    AskResponse,
    EntityMention,
    EvidenceItemType,
    LLMInfo,
    RetrievalSummary,
    SupportLevel,
)
from vedagraph.api.models.common import CaveatView, KnowledgeStatus
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.llm.base import LLMProvider

logger = logging.getLogger(__name__)

#: Support levels worst-first, so a downgrade can be taken as a minimum rather than an
#: assignment. Writing ``support_level = LIMITED`` would *raise* an INSUFFICIENT grade.
_SUPPORT_ORDER: Final[tuple[SupportLevel, ...]] = (
    SupportLevel.INSUFFICIENT,
    SupportLevel.LIMITED,
    SupportLevel.MODERATE,
    SupportLevel.STRONG,
)

#: Follow-up questions are offered per intent rather than generated. A second model call
#: to invent them doubles the latency and the bill of every request, and the useful next
#: questions in a bounded domain are knowable in advance.
_FOLLOW_UPS: Final[dict[str, tuple[str, ...]]] = {
    "ENTITY_PROFILE": (
        "Which hymns are dedicated to {subject}, as opposed to merely mentioning it?",
        "How is {subject} distributed across the four corpora?",
    ),
    "CROSS_VEDA": (
        "Which corpora does this annotation layer not reach?",
        "Are there textual parallels for {subject} between the corpora?",
    ),
    "PASSAGE_LOOKUP": (
        "Is this verse reused or paralleled elsewhere in the corpus?",
        "Which deities and seers is this verse attributed to?",
    ),
    "GRAPH_CONNECTION": (
        "What kind of evidence supports each edge on that path?",
        "Do {subject} co-occur in the same verses?",
    ),
    "FORMULA": (
        "Which corpora does this formula family span?",
        "Are the occurrences textual parallels or independent uses?",
    ),
    "HUMAN_CONCERN": (
        "Which Atharvavedic hymns address this condition?",
        "Is this modelled as an affliction, a threat, or a cause?",
    ),
    "INTERPRETIVE_CLAIM": (
        "What would falsify that interpretation?",
        "Is there a competing reading in VedaGraph?",
    ),
}

_GENERIC_FOLLOW_UPS: Final[tuple[str, ...]] = (
    "Which parts of this question does VedaGraph not cover?",
    "What evidence supports the strongest claim in that answer?",
)


def _follow_ups(intents: list[str], subject: str | None) -> list[str]:
    out: list[str] = []
    for intent in intents:
        for template in _FOLLOW_UPS.get(intent, ()):
            if "{subject}" in template:
                if not subject:
                    continue
                out.append(template.format(subject=subject))
            else:
                out.append(template)
    out.extend(_GENERIC_FOLLOW_UPS)
    return list(dict.fromkeys(out))[:3]


class AskService:
    """Orchestrates one Ask request."""

    def __init__(self, repository: Neo4jRepository, llm_provider: LLMProvider) -> None:
        self._repo = repository
        self._llm = llm_provider

    def ask(self, request: AskRequest) -> AskResponse:
        started = time.monotonic()

        plan = planner_stage.plan(request.question, explicit_veda=request.veda, mode=request.mode)

        # Page context is a caller-supplied identifier ("ask about this mantra"), so it
        # is trusted as a *subject* and still resolved through the same path as anything
        # the planner found. It is never interpolated anywhere.
        if request.passage_context and not plan.passage_key:
            plan.passage_key = request.passage_context
        if request.entity_context:
            plan.entities_mentioned.insert(0, request.entity_context)
            if "entities" not in plan.retrieval_channels:
                plan.retrieval_channels.insert(0, "entities")

        resolved = resolver_stage.resolve_entities(plan.entities_mentioned, self._repo)
        retrieval = retriever_stage.retrieve(plan, resolved, self._repo)
        packet = evidence_stage.build_evidence_packet(retrieval)

        history = [(turn.role, turn.content) for turn in (request.conversation_context or [])]
        synthesis = synthesis_stage.synthesize(
            question=request.question,
            packet=packet,
            intents=plan.intents,
            provider=self._llm,
            veda_scope=plan.veda_scope,
            mode=request.mode,
            conversation_context=history or None,
        )

        audited = citation_stage.audit(synthesis.answer, packet)

        # Re-grade against the citations that survived the audit. Grading on the model's
        # claimed citations would let an invented id inflate the support level of the
        # very answer the audit just found unsupported.
        status, support_level = synthesis_stage.assess_support(
            packet,
            [c.id for c in audited.citations],
            degraded=synthesis.degraded,
        )

        # Two ways an answer can be well-cited and still not be a finished, faithful
        # one. Neither is visible to citation grading, and both were shipped silently
        # before: a summary that contradicted its own figures was returned SUPPORTED,
        # and four benchmark answers stopped at the output cap with nothing saying so.
        # Grading is the last thing to move so it sees the outcome of every check.
        if status is KnowledgeStatus.SUPPORTED and (
            not synthesis.quantitative.ok or synthesis.generation_truncated
        ):
            status = KnowledgeStatus.PARTIAL
            support_level = min(support_level, SupportLevel.LIMITED, key=_SUPPORT_ORDER.index)

        caveats = self._caveats(plan, retrieval, packet, audited, status, synthesis)
        subject = resolved[0].label if resolved else None

        total_ms = (time.monotonic() - started) * 1000

        return AskResponse(
            answer=audited.cleaned_answer or synthesis.answer,
            status=status,
            support_level=support_level,
            citations=audited.citations,
            evidence=packet.items,
            entities=self._entities(plan, resolved),
            related_questions=_follow_ups([i.value for i in plan.intents], subject),
            caveats=caveats,
            retrieval_summary=RetrievalSummary(
                channels_used=retrieval.channels_used,
                channels_empty=retrieval.channels_empty,
                intents=[i.value for i in plan.intents],
                entities_resolved=[e.label for e in resolved],
                entities_unresolved=[
                    name
                    for name in plan.entities_mentioned
                    if not any(e.name_as_asked == name for e in resolved)
                ],
                veda_scope=plan.veda_scope,
                evidence_count=len(packet.items),
                planner_ms=round(plan.planning_ms, 2),
                retrieval_ms=round(retrieval.retrieval_ms, 2),
                synthesis_ms=round(synthesis.synthesis_ms, 2),
                total_ms=round(total_ms, 2),
            ),
            interpretive_content_present=packet.has_interpretive_content(),
            llm=LLMInfo(provider=synthesis.provider, model=synthesis.model),
        )

    @staticmethod
    def _entities(
        plan: planner_stage.QueryPlan, resolved: list[resolver_stage.ResolvedEntity]
    ) -> list[EntityMention]:
        mentions = [
            EntityMention(
                label=entity.label,
                entity_key=entity.entity_key,
                entity_type=entity.entity_type,
                resolved=True,
                asked_as=entity.name_as_asked,
                match_rank=entity.match_rank.name,
            )
            for entity in resolved
        ]
        # An unresolved name is reported rather than dropped: "VedaGraph has no entity
        # called Shiva" is a real and useful answer to a question about Shiva, and it is
        # the answer a silently shortened list hides.
        for name in plan.entities_mentioned:
            if not any(e.name_as_asked == name for e in resolved):
                mentions.append(EntityMention(label=name, resolved=False, asked_as=name))
        return mentions[:12]

    @staticmethod
    def _caveats(
        plan: planner_stage.QueryPlan,
        retrieval: retriever_stage.RetrievalResult,
        packet: evidence_stage.EvidencePacket,
        audited: citation_stage.CitationAudit,
        status: KnowledgeStatus,
        synthesis: synthesis_stage.SynthesisResult,
    ) -> list[CaveatView]:
        caveats: list[CaveatView] = []

        if synthesis.generation_truncated:
            # Deliberately says nothing about finish reasons or token caps. The reader
            # needs to know the text stops early and the evidence does not.
            caveats.append(
                CaveatView(
                    text=(
                        "The generated response reached its output limit and may be "
                        "incomplete. The supporting VedaGraph evidence remains available "
                        "below."
                    ),
                    source="generation_truncated",
                )
            )

        if not synthesis.quantitative.ok:
            caveats.append(
                CaveatView(
                    text=synthesis.quantitative.summary(),
                    source="quantitative_audit",
                )
            )

        if audited.invented_ids:
            caveats.append(
                CaveatView(
                    text=(
                        f"{len(audited.invented_ids)} citation marker(s) in the draft "
                        "answer referred to evidence that does not exist and were "
                        "removed. Treat any uncited sentence as unsupported."
                    ),
                    source="citation_audit",
                )
            )

        if audited.unverified_quotes:
            quoted = ", ".join(audited.unverified_quotes[:3])
            caveats.append(
                CaveatView(
                    text=(
                        f"The answer contains Sanskrit ({quoted}) that appears nowhere "
                        "in the retrieved evidence. Treat it as unverified: it may not "
                        "be a quotation from this corpus at all."
                    ),
                    source="quote_audit",
                )
            )

        if audited.uncited_quotes:
            # Deliberately worded as a provenance note rather than a warning. The
            # wording is real and was retrieved; the answer pointed at the wrong id.
            quoted = ", ".join(audited.uncited_quotes[:3])
            caveats.append(
                CaveatView(
                    text=(
                        f"The Sanskrit quoted here ({quoted}) is in the retrieved "
                        "evidence but in an item the answer did not cite. The wording "
                        "is genuine; the citation beside it points elsewhere."
                    ),
                    source="quote_provenance",
                )
            )

        if not packet.items:
            caveats.append(
                CaveatView(
                    text=(
                        "No VedaGraph channel returned evidence for this question, so "
                        "nothing here is grounded in the graph. This is not a finding "
                        "about the Vedas."
                    ),
                    source="retrieval",
                )
            )
        elif not audited.citations:
            # Retrieval succeeded and the answer cited none of it. Support grading is
            # citation-derived, so this lands on INSUFFICIENT_EVIDENCE -- a status that
            # on its own reads as "the graph cannot answer this". It did answer: it
            # returned evidence and the prose failed to attach itself to it. Naming the
            # difference matters, because the two call for opposite responses from a
            # reader: one means look elsewhere, the other means check these items.
            caveats.append(
                CaveatView(
                    text=(
                        f"Retrieval returned {len(packet.items)} evidence item(s) but the "
                        "answer cites none of them, so no sentence in it can be traced to "
                        "a source. The status reflects that missing link, not an empty "
                        "graph: read the evidence below directly."
                    ),
                    source="uncited_answer",
                )
            )

        if packet.unsearchable_vedas:
            caveats.append(
                CaveatView(
                    text=(
                        "These corpora carry no searchable surface for this query, so "
                        "their zero is about this project's coverage and not about the "
                        f"text: {', '.join(packet.unsearchable_vedas)}."
                    ),
                    source="lexical_surface",
                )
            )

        if retrieval.lexical is not None:
            found = retrieval.lexical.found_in()
            missing = [
                str(row["veda"]) for row in retrieval.lexical.rows if str(row["veda"]) not in found
            ]
            if missing:
                caveats.append(
                    CaveatView(
                        text=(
                            f"'{retrieval.lexical.term}' was not matched in "
                            f"{', '.join(sorted(missing))}. A lexical miss is bounded by "
                            "that corpus's searchable surface and its accentuation, and "
                            "must not be read as the text not containing the term."
                        ),
                        source="lexical_presence",
                    )
                )

        has_ambiguity_evidence = any(
            item.type is EvidenceItemType.CORPUS_DISTRIBUTION for item in packet.items
        )
        if has_ambiguity_evidence:
            caveats.append(
                CaveatView(
                    text=(
                        "Deity counts here include CERTAIN and PROBABLE referents and "
                        "exclude AMBIGUOUS ones, because a deity's name in Vedic "
                        "Sanskrit is also an ordinary noun. The excluded figures are "
                        "stated in the evidence."
                    ),
                    source="referent_certainty",
                )
            )

        if packet.has_interpretive_content():
            caveats.append(
                CaveatView(
                    text=(
                        "This answer draws on an InterpretiveClaim: a reading recorded "
                        "in VedaGraph with a named source, not a statement of the text."
                    ),
                    source="interpretive_layer",
                )
            )

        # Only when the status really is about coverage. Where evidence was retrieved and
        # simply not cited, the `uncited_answer` caveat above already gives the accurate
        # reason, and adding this one would contradict it -- telling the reader in one
        # line that the graph has no coverage and in the next that it returned fourteen
        # items. Two caveats that disagree are worse than either alone: the reader cannot
        # tell which to act on.
        coverage_is_the_reason = not packet.items or bool(audited.citations)
        if status is KnowledgeStatus.INSUFFICIENT_EVIDENCE and coverage_is_the_reason:
            caveats.append(
                CaveatView(
                    text=(
                        "VedaGraph's evidence does not establish an answer to this "
                        "question. That is a statement about this graph's coverage, not "
                        "about the Vedic corpus."
                    ),
                    source="support_grading",
                )
            )

        if retrieval.channels_empty:
            caveats.append(
                CaveatView(
                    text=(
                        "These retrieval channels ran and returned nothing: "
                        f"{', '.join(sorted(set(retrieval.channels_empty)))}. They were "
                        "searched; they are not unexamined."
                    ),
                    source="retrieval",
                )
            )

        return caveats
