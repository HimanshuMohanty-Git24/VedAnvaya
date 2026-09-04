"""Coverage and frequency analytics over deterministic knowledge assertions.

Every count here measures **traditional metadata assignment**. ``HAS_DEVATA: agniḥ``
means the Anukramaṇī assigns Agni as this mantra's devatā; it does not mean the word
*agni* occurs in the Sanskrit. Literal occurrence is a different metric and belongs to a
later deterministic lexical phase.
"""

from __future__ import annotations

from collections import defaultdict

from vedagraph.knowledge.build import PREDICATE_WHITELIST, CorpusIndex, KnowledgeBuildResult
from vedagraph.models.enums import KnowledgeEntityType, MetadataPredicate
from vedagraph.models.knowledge import (
    PREDICATE_ENTITY_TYPE,
    EntityFrequency,
    KnowledgeAssertion,
    KnowledgeCoverage,
    KnowledgeStats,
)

ASSIGNMENT_METRIC = (
    "Counts are mantra occurrences carrying a traditional metadata assignment, not "
    "occurrences of the entity's name in the Sanskrit text."
)


def _sukta_of(subject_key: str) -> str:
    return subject_key.rsplit(":", 1)[0]


def coverage(
    assertions: list[KnowledgeAssertion],
    corpus: CorpusIndex,
    unresolved_mantras: dict[MetadataPredicate, int],
    claimed: dict[MetadataPredicate, set[str]],
) -> list[KnowledgeCoverage]:
    resolved: dict[MetadataPredicate, dict[str, set[str]]] = {
        predicate: defaultdict(set) for predicate in PREDICATE_WHITELIST
    }
    counts: dict[MetadataPredicate, int] = dict.fromkeys(PREDICATE_WHITELIST, 0)
    for assertion in assertions:
        resolved[assertion.predicate][assertion.subject_key].add(assertion.object_key)
        counts[assertion.predicate] += 1
    total = corpus.total_mantras
    report: list[KnowledgeCoverage] = []
    for predicate in PREDICATE_WHITELIST:
        by_mantra = resolved[predicate]
        entities = {key for keys in by_mantra.values() for key in keys}
        with_claim = len(claimed[predicate])
        report.append(
            KnowledgeCoverage(
                predicate=predicate,
                total_mantras=total,
                mantras_with_source_claim=with_claim,
                mantras_resolved=len(by_mantra),
                mantras_unresolved_only=with_claim - len(by_mantra),
                mantras_without_claim=total - with_claim,
                mantras_with_multiple_entities=sum(
                    1 for keys in by_mantra.values() if len(keys) > 1
                ),
                assertion_count=counts[predicate],
                distinct_entities=len(entities),
            )
        )
    return report


def frequencies(
    result: KnowledgeBuildResult, entity_type: KnowledgeEntityType, limit: int = 25
) -> list[EntityFrequency]:
    labels = {entity.entity_key: entity.preferred_label for entity in result.entities[entity_type]}
    mantras: dict[str, set[str]] = defaultdict(set)
    suktas: dict[str, set[str]] = defaultdict(set)
    for assertion in result.assertions:
        if PREDICATE_ENTITY_TYPE[assertion.predicate] is not entity_type:
            continue
        mantras[assertion.object_key].add(assertion.subject_key)
        suktas[assertion.object_key].add(_sukta_of(assertion.subject_key))
    ranked = sorted(
        mantras,
        key=lambda key: (-len(mantras[key]), key),
    )
    return [
        EntityFrequency(
            entity_key=key,
            preferred_label=labels[key],
            entity_type=entity_type,
            mantra_assignment_count=len(mantras[key]),
            sukta_count=len(suktas[key]),
        )
        for key in ranked[:limit]
    ]


def build_stats(result: KnowledgeBuildResult, *, top: int = 25) -> KnowledgeStats:
    claimed: dict[MetadataPredicate, set[str]] = {
        predicate: set() for predicate in PREDICATE_WHITELIST
    }
    for source in result.source_assertions:
        mandala, sukta = _sukta_address(source.subject_key)
        span = (
            range(1, result.corpus.mantra_counts[(mandala, sukta)] + 1)
            if source.start_mantra is None
            else range(source.start_mantra, (source.end_mantra or source.start_mantra) + 1)
        )
        for mantra in span:
            key = result.corpus.mantra_keys.get((mandala, sukta, mantra))
            if key is not None:
                claimed[source.predicate].add(key)
    unresolved_mantras: dict[MetadataPredicate, int] = defaultdict(int)
    unresolved_counts: dict[str, int] = defaultdict(int)
    for label in result.unresolved:
        unresolved_mantras[label.predicate] += label.mantra_count
        unresolved_counts[label.entity_type.value] += 1
    return KnowledgeStats(
        metric_definition=ASSIGNMENT_METRIC,
        total_mantras=result.corpus.total_mantras,
        total_suktas=result.corpus.total_suktas,
        dataset_rows=result.alignment.dataset_rows,
        aligned_rows=result.alignment.aligned_rows,
        unaligned_rows=len(result.alignment.unaligned_rows),
        duplicate_row_mappings=len(result.alignment.duplicate_rows),
        missing_corpus_suktas=len(result.alignment.missing_corpus_suktas),
        source_assertions=len(result.source_assertions),
        knowledge_assertions=len(result.assertions),
        coverage=coverage(result.assertions, result.corpus, dict(unresolved_mantras), claimed),
        entity_counts={
            entity_type.value: len(entities) for entity_type, entities in result.entities.items()
        },
        unresolved_label_counts=dict(sorted(unresolved_counts.items())),
        top_rishis=frequencies(result, KnowledgeEntityType.RISHI, top),
        top_devatas=frequencies(result, KnowledgeEntityType.DEVATA, top),
        top_chandas=frequencies(result, KnowledgeEntityType.CHANDAS, top),
        composite_devata_count=sum(
            1 for entity in result.entities[KnowledgeEntityType.DEVATA] if entity.is_composite
        ),
    )


def _sukta_address(sukta_key: str) -> tuple[int, int]:
    parts = sukta_key.split(":")
    return int(parts[3][1:]), int(parts[4][1:])
