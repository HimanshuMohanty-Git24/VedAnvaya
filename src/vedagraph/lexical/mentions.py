"""Build ``MENTIONS_ENTITY`` edges from annotated tokens, with token-level evidence.

A ``MENTIONS_ENTITY`` assertion says only this: the Sanskrit of this mantra contains a
word whose annotated lemma resolves to this canonical entity. It says nothing about who
the mantra is *addressed* to. That is ``HAS_DEVATA``, it comes from the Anukramaṇī, and
it lives in a different file built by a different pipeline.

Every assertion carries the tokens it rests on, so a reader can be shown the exact word,
in the exact pāda, that produced the edge. A mantra naming one entity several times
yields one edge with several evidence tokens: the graph stays simple, the textual record
stays complete.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from vedagraph.identity import uuid_for_urn
from vedagraph.lexical.aliases import MENTION_POLICY_VERSION, AliasMatch, LexicalMatcher
from vedagraph.models.enums import LexicalMatchStatus, MentionMethod
from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.models.lexical import (
    AmbiguousMention,
    MentionAssertion,
    MentionEvidence,
    MorphologyToken,
)


def mention_identity(subject_key: str, object_key: str) -> tuple[str, UUID]:
    """One mantra, one entity, one edge. Occurrences live in the evidence list."""
    urn = f"urn:vedagraph:assertion:mentions_entity:{subject_key.lower()}:{object_key.lower()}"
    return urn, uuid_for_urn(urn)


def build_mentions(
    tokens: list[MorphologyToken],
    matcher: LexicalMatcher,
    entities: dict[str, KnowledgeEntity],
    *,
    citations: dict[str, str],
    passage_ids: dict[str, UUID],
) -> tuple[list[MentionAssertion], list[AmbiguousMention]]:
    """Return the accepted mention edges and the deliberately unresolved tokens."""
    grouped: dict[tuple[str, str], list[tuple[MorphologyToken, AliasMatch]]] = defaultdict(list)
    ambiguous: list[AmbiguousMention] = []

    for token in tokens:
        result = matcher.match(token)
        if result.status is LexicalMatchStatus.MATCHED:
            assert result.alias is not None
            grouped[(token.passage_key, result.alias.entity_key)].append((token, result))
            continue
        if result.status in {
            LexicalMatchStatus.AMBIGUOUS_LEXICAL_ENTITY,
            LexicalMatchStatus.AMBIGUOUS_SOURCE_LEMMA,
        }:
            ambiguous.append(
                AmbiguousMention(
                    passage_key=token.passage_key,
                    token_key=token.token_key,
                    lemma=token.lemma,
                    normalized_lemma=token.normalized_lemma,
                    surface=token.surface_form,
                    status=result.status,
                    candidate_entity_keys=list(result.candidates),
                    reason=result.reason,
                )
            )

    assertions: list[MentionAssertion] = []
    for (passage_key, entity_key), hits in grouped.items():
        entity = entities[entity_key]
        ordered = sorted(hits, key=lambda item: item[0].sequence)
        evidence = [
            MentionEvidence(
                token_id=token.token_id,
                token_key=token.token_key,
                sequence=token.sequence,
                pada=token.pada,
                surface=token.surface_form,
                lemma=token.lemma,
                alias_id=match.alias.alias_id,  # type: ignore[union-attr]
                alias_key=match.alias.alias_key,  # type: ignore[union-attr]
                method=match.method or MentionMethod.LEMMA_ID_EXACT,
            )
            for token, match in ordered
        ]
        _, assertion_id = mention_identity(passage_key, entity_key)
        assertions.append(
            MentionAssertion(
                assertion_id=assertion_id,
                subject_key=passage_key,
                subject_id=passage_ids[passage_key],
                object_key=entity_key,
                object_id=entity.entity_id,
                entity_type=entity.entity_type,
                occurrence_count=len(evidence),
                evidence=evidence,
                methods=sorted({item.method for item in evidence}),
                annotation_layer_id=ordered[0][0].annotation_layer_id,
                source_artifact_ids=sorted({token.source_artifact_id for token, _ in ordered}),
                mention_policy_version=MENTION_POLICY_VERSION,
                citation=citations[passage_key],
            )
        )

    assertions.sort(key=lambda item: (item.subject_key, item.object_key))
    ambiguous.sort(key=lambda item: item.token_key)
    return assertions, ambiguous
