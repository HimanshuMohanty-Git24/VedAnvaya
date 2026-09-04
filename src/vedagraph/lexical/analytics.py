"""Deterministic analytics that keep assignment and mention permanently apart.

There is no single number for "the most important deity", and this module refuses to
produce one. It computes three different counts:

``mantra_assignment_count``
    how many mantras the Anukramaṇī assigns to the entity (``HAS_DEVATA``).
``mantra_mention_count``
    how many mantras contain a word that lexically names the entity.
``token_occurrence_count``
    how many individual words across the corpus resolve to the entity.

They rank differently, and the difference is the interesting result rather than a
discrepancy to be smoothed away. Any caller that collapses them back into one figure is
answering a question none of the three asks.

Co-occurrence is likewise an observation with a stated unit, not a relationship. Nothing
here emits a ``RELATED_TO`` edge, and the counts are not evidence of one.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from vedagraph.models.enums import KnowledgeEntityType, MetadataPredicate, ParallelStatus
from vedagraph.models.knowledge import KnowledgeAssertion, KnowledgeEntity
from vedagraph.models.lexical import (
    EntityCoOccurrence,
    EntityLexicalFrequency,
    ExactParallelGroup,
    LexicalAlias,
    LexicalAliasCandidate,
    LexicalStats,
    MandalaMentionStats,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
    ParallelCandidate,
)

METRIC_DEFINITIONS = {
    "mantra_assignment_count": (
        "Mantras whose traditional Anukramaṇī metadata assigns this entity "
        "(HAS_DEVATA / HAS_RISHI). This is attribution, not vocabulary."
    ),
    "mantra_mention_count": (
        "Mantras whose Sanskrit text contains at least one token whose annotated "
        "lemma resolves to this entity (MENTIONS_ENTITY). This is vocabulary, not "
        "attribution."
    ),
    "token_occurrence_count": (
        "Total annotated tokens across the corpus resolving to this entity. A mantra "
        "naming an entity three times contributes three."
    ),
    "co_occurrence": (
        "Mantras in which two entities are both lexically mentioned. Unit: MANTRA. "
        "A statistical observation only; it asserts no relationship between them."
    ),
    "warning": (
        "These three counts answer three different questions and routinely rank "
        "differently. None of them means 'the most used god'."
    ),
}

TOP_N = 25


def _mandala_of(passage_key: str) -> int:
    return int(passage_key.split(":")[3][1:])


def build_lexical_stats(
    *,
    tokens: list[MorphologyToken],
    entities: dict[str, KnowledgeEntity],
    aliases: list[LexicalAlias],
    alias_candidates: list[LexicalAliasCandidate],
    mentions: list[MentionAssertion],
    ambiguous_count: int,
    knowledge_assertions: list[KnowledgeAssertion],
    parallels: list[MantraParallel],
    parallel_candidates: list[ParallelCandidate],
    exact_groups: list[ExactParallelGroup],
    component_count: int,
    total_mantras: int,
) -> tuple[LexicalStats, list[EntityCoOccurrence]]:
    mention_mantras: dict[str, set[str]] = defaultdict(set)
    token_occurrences: Counter[str] = Counter()
    for mention in mentions:
        mention_mantras[mention.object_key].add(mention.subject_key)
        token_occurrences[mention.object_key] += mention.occurrence_count

    assignment_mantras: dict[str, set[str]] = defaultdict(set)
    for assertion in knowledge_assertions:
        if assertion.predicate in {MetadataPredicate.HAS_DEVATA, MetadataPredicate.HAS_RISHI}:
            assignment_mantras[assertion.object_key].add(assertion.subject_key)

    def frequency(entity_key: str) -> EntityLexicalFrequency:
        entity = entities[entity_key]
        assigned = assignment_mantras.get(entity_key, set())
        mentioned = mention_mantras.get(entity_key, set())
        return EntityLexicalFrequency(
            entity_key=entity_key,
            preferred_label=entity.preferred_label,
            entity_type=entity.entity_type,
            mantra_assignment_count=len(assigned),
            mantra_mention_count=len(mentioned),
            token_occurrence_count=token_occurrences.get(entity_key, 0),
            assigned_and_mentioned_count=len(assigned & mentioned),
            assigned_not_mentioned_count=len(assigned - mentioned),
            mentioned_not_assigned_count=len(mentioned - assigned),
        )

    def top(
        keys: set[str], entity_type: KnowledgeEntityType, sort_key: str
    ) -> list[EntityLexicalFrequency]:
        rows = [frequency(key) for key in keys if entities[key].entity_type is entity_type]
        rows = [row for row in rows if getattr(row, sort_key) > 0]
        rows.sort(key=lambda row: (-getattr(row, sort_key), row.entity_key))
        return rows[:TOP_N]

    known = set(assignment_mantras) | set(mention_mantras)
    known = {key for key in known if key in entities}

    # Co-occurrence: for each mantra, every unordered pair of entities mentioned in it.
    per_mantra: dict[str, set[str]] = defaultdict(set)
    for mention in mentions:
        per_mantra[mention.subject_key].add(mention.object_key)
    pair_counts: Counter[tuple[str, str]] = Counter()
    for entity_keys in per_mantra.values():
        ordered = sorted(entity_keys)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                pair_counts[(left, right)] += 1
    co_occurrences = sorted(
        (
            EntityCoOccurrence(
                left_entity_key=left,
                right_entity_key=right,
                left_label=entities[left].preferred_label,
                right_label=entities[right].preferred_label,
                count=count,
            )
            for (left, right), count in pair_counts.items()
        ),
        key=lambda row: (-row.count, row.left_entity_key, row.right_entity_key),
    )

    mantras_by_mandala: Counter[int] = Counter()
    for token in tokens:
        mantras_by_mandala[_mandala_of(token.passage_key)] = mantras_by_mandala.get(
            _mandala_of(token.passage_key), 0
        )
    mandala_mantras: dict[int, set[str]] = defaultdict(set)
    for token in tokens:
        mandala_mantras[_mandala_of(token.passage_key)].add(token.passage_key)
    mandala_mentioned: dict[int, set[str]] = defaultdict(set)
    mandala_assertions: Counter[int] = Counter()
    mandala_tokens: Counter[int] = Counter()
    for mention in mentions:
        mandala = _mandala_of(mention.subject_key)
        mandala_mentioned[mandala].add(mention.subject_key)
        mandala_assertions[mandala] += 1
        mandala_tokens[mandala] += mention.occurrence_count

    stats = LexicalStats(
        metric_definitions=METRIC_DEFINITIONS,
        total_mantras=total_mantras,
        mantras_with_morphology=len({token.passage_key for token in tokens}),
        total_tokens=len(tokens),
        tokens_with_lemma=sum(1 for token in tokens if token.lemma),
        distinct_lemmas=len({token.normalized_lemma for token in tokens}),
        accepted_lexical_aliases=sum(1 for alias in aliases if alias.may_produce_mention),
        do_not_match_aliases=sum(
            1 for alias in aliases if alias.alias_type.value == "DO_NOT_MATCH"
        ),
        alias_candidates=len(alias_candidates),
        mention_assertions=len(mentions),
        mention_token_occurrences=sum(mention.occurrence_count for mention in mentions),
        mantras_with_mentions=len(per_mantra),
        mantras_without_mentions=total_mantras - len(per_mantra),
        ambiguous_mentions=ambiguous_count,
        mentions_by_method=dict(
            sorted(
                Counter(
                    item.method.value for mention in mentions for item in mention.evidence
                ).items()
            )
        ),
        top_assigned_devatas=top(known, KnowledgeEntityType.DEVATA, "mantra_assignment_count"),
        top_mentioned_devatas=top(known, KnowledgeEntityType.DEVATA, "mantra_mention_count"),
        top_token_occurrence_entities=top(
            known, KnowledgeEntityType.DEVATA, "token_occurrence_count"
        ),
        top_assigned_rishis=top(known, KnowledgeEntityType.RISHI, "mantra_assignment_count"),
        top_mentioned_rishis=top(known, KnowledgeEntityType.RISHI, "mantra_mention_count"),
        top_co_occurrences=co_occurrences[:TOP_N],
        mentions_by_mandala=[
            MandalaMentionStats(
                mandala=mandala,
                mantras=len(mandala_mantras.get(mandala, set())),
                mantras_with_mentions=len(mandala_mentioned.get(mandala, set())),
                mention_assertions=mandala_assertions.get(mandala, 0),
                token_occurrences=mandala_tokens.get(mandala, 0),
            )
            for mandala in sorted(mandala_mantras)
        ],
        exact_parallel_pairs=sum(
            1 for item in parallels if item.status is ParallelStatus.EXACT_PARALLEL
        ),
        exact_parallel_groups=len(exact_groups),
        largest_exact_group=max((group.size for group in exact_groups), default=0),
        near_parallel_candidates=len(parallel_candidates),
        accepted_near_parallels=sum(
            1 for item in parallels if item.status is ParallelStatus.HIGH_CONFIDENCE_NEAR_PARALLEL
        ),
        component_assertions=component_count,
    )
    return stats, co_occurrences
