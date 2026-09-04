"""Resolve a proposed concept against the registries, or refuse to.

The failure mode this module exists to prevent is specific and it is the one that ruins
semantic knowledge graphs: *Creation*, *Cosmic Creation*, *Creation of the Universe*,
*Cosmogony* and *Origin of the Cosmos* becoming five nodes with a fifth of the evidence
each. Nothing downstream recovers from that, because by then the graph looks populated.

The rule that prevents it is not "merge aggressively". It is:

**Exact identity may merge. Similarity may only ask.** A proposal reaching an existing
row by normalized label or by a reviewed alias is that row. A proposal that merely
*looks like* one is a review candidate carrying both labels, and it creates nothing.
``Cosmic Order`` and ``Ṛta`` may well be one entity; they may also be a Vedic term and a
translator's gloss of it, and that difference is not settled by string distance.

No embedding similarity is used in this phase, in either direction. Character-level
similarity appears once, as a *brake*: it can withhold automatic acceptance of a new
entity and raise a review candidate, and it can do nothing else.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import yaml

from vedagraph.models.enums import SemanticEntityResolution
from vedagraph.models.semantic import SemanticEntityCandidate, SemanticEntityRegistryRow
from vedagraph.semantic.ontology import SemanticNodeType

SEMANTIC_ENTITY_FILE = "semantic_entities.yaml"
REGISTRY_POLICY_VERSION = "rigveda-semantic-entity-registry-v1"

#: Below this, a new entity is proposed but not automatically accepted: too close to an
#: existing row to be created without a person looking at both. It never merges anything.
REVIEW_SIMILARITY = 0.82

#: A brand-new concept seen in only one mantra is usually a phrasing, not an entity.
MIN_EVIDENCE_FOR_NEW_ENTITY = 2

_NON_WORD = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")

#: Words that carry no distinguishing force in an English concept label. Stripping them
#: is a *normalization*, so "the sacrifice" and "sacrifice" are the same proposal. It is
#: not a synonym rule: "cosmic order" and "order" stay different strings.
_STOPWORDS = frozenset({"a", "an", "the", "of", "and", "or", "to", "in", "for"})


def normalize_label(label: str) -> str:
    """Fold a proposed label to its comparison form.

    Diacritics are folded because a model will write ``ṛta``, ``rta`` and ``Ṛta`` for the
    same proposal and none of those differences is a claim. Nothing else is merged.
    """
    decomposed = unicodedata.normalize("NFKD", label)
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    lowered = _NON_WORD.sub(" ", ascii_only.casefold())
    words = [word for word in _SPACES.split(lowered) if word and word not in _STOPWORDS]
    return " ".join(words) or _SPACES.sub(" ", lowered).strip()


def candidate_id(entity_type: SemanticNodeType, label: str) -> str:
    """Identity of a proposal: its type and its normalized label, and nothing else.

    Deriving it this way is what makes the same concept proposed from forty mantras one
    candidate with an evidence count of forty, rather than forty candidates.
    """
    slug = normalize_label(label).replace(" ", "_").upper() or "UNLABELLED"
    return f"SEMCAND:{entity_type.value}:{slug}"


def entity_key(entity_type: SemanticNodeType, label: str) -> str:
    slug = normalize_label(label).replace(" ", "_").upper() or "UNLABELLED"
    return f"VG:SEM:{entity_type.value}:{slug}"


def load_semantic_entities(registry_root: Path) -> dict[str, SemanticEntityRegistryRow]:
    """Read the reviewed semantic entity registry. An absent file means an empty registry.

    Empty is the correct starting state. Seeding it with ṛta, satya and vāc would be
    writing the answers into the question the pilot exists to ask.
    """
    path = registry_root / SEMANTIC_ENTITY_FILE
    if not path.exists():
        return {}
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    declared = str(document.get("policy_version", ""))
    if declared != REGISTRY_POLICY_VERSION:
        raise ValueError(
            f"{path} declares policy_version {declared!r}, expected {REGISTRY_POLICY_VERSION!r}"
        )
    rows: dict[str, SemanticEntityRegistryRow] = {}
    for raw in document.get("entities", []):
        node_type = SemanticNodeType(raw["entity_type"])
        row = SemanticEntityRegistryRow(
            entity_key=str(raw.get("entity_key") or entity_key(node_type, str(raw["label"]))),
            entity_type=node_type,
            preferred_label=str(raw["label"]),
            normalized_label=normalize_label(str(raw["label"])),
            aliases=[str(item) for item in raw.get("aliases", [])],
            description=str(raw.get("description", "")),
            evidence=str(raw["evidence"]),
        )
        if row.entity_key in rows:
            raise ValueError(f"{path}: duplicate semantic entity {row.entity_key}")
        rows[row.entity_key] = row
    return rows


@dataclass(frozen=True)
class ResolutionIndex:
    """Lookup surfaces for the reviewed registry, built once per run."""

    rows: dict[str, SemanticEntityRegistryRow]
    by_normalized: dict[tuple[SemanticNodeType, str], str]
    by_alias: dict[tuple[SemanticNodeType, str], str]

    @classmethod
    def build(cls, rows: dict[str, SemanticEntityRegistryRow]) -> ResolutionIndex:
        by_normalized: dict[tuple[SemanticNodeType, str], str] = {}
        by_alias: dict[tuple[SemanticNodeType, str], str] = {}
        for row in rows.values():
            by_normalized[(row.entity_type, row.normalized_label)] = row.entity_key
            for alias in row.aliases:
                by_alias[(row.entity_type, normalize_label(alias))] = row.entity_key
        return cls(rows=rows, by_normalized=by_normalized, by_alias=by_alias)

    def similar_keys(self, node_type: SemanticNodeType, normalized: str) -> list[str]:
        """Registry rows close enough that a person should compare them. Merges nothing."""
        hits = [
            row.entity_key
            for row in self.rows.values()
            if row.entity_type is node_type
            and SequenceMatcher(None, row.normalized_label, normalized).ratio() >= REVIEW_SIMILARITY
        ]
        return sorted(hits)


@dataclass
class _Accumulator:
    entity_type: SemanticNodeType
    preferred_label: str
    normalized_label: str
    description: str = ""
    aliases: set[str] = None  # type: ignore[assignment]
    passages: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.aliases = self.aliases or set()
        self.passages = self.passages or set()


def resolve_entity_candidates(
    proposals: list[tuple[str, SemanticNodeType, str, str, list[str]]],
    index: ResolutionIndex,
    *,
    model: str,
    prompt_version: str,
    ontology_version: str,
) -> list[SemanticEntityCandidate]:
    """Group proposals by identity, then resolve each group against the registry.

    ``proposals`` are ``(passage_key, node_type, label, description, aliases)`` tuples in
    the order the extraction produced them. The first label seen for a candidate becomes
    its preferred label and every other spelling becomes an alias of *the candidate*,
    which is a statement about one proposal and not about the registry.
    """
    grouped: dict[str, _Accumulator] = {}
    for passage_key, node_type, label, description, aliases in proposals:
        key = candidate_id(node_type, label)
        entry = grouped.get(key)
        if entry is None:
            entry = _Accumulator(
                entity_type=node_type,
                preferred_label=label,
                normalized_label=normalize_label(label),
                description=description,
            )
            grouped[key] = entry
        elif label != entry.preferred_label:
            entry.aliases.add(label)
        entry.aliases.update(aliases)
        entry.passages.add(passage_key)

    resolved: list[SemanticEntityCandidate] = []
    for key, entry in sorted(grouped.items()):
        lookup = (entry.entity_type, entry.normalized_label)
        matched = index.by_normalized.get(lookup) or index.by_alias.get(lookup)
        similar = index.similar_keys(entry.entity_type, entry.normalized_label)
        if matched is not None:
            resolution = SemanticEntityResolution.MATCHED_EXISTING_ENTITY
            reason = "normalized label or reviewed alias is an exact registry hit"
            similar = [item for item in similar if item != matched]
        elif similar:
            resolution = SemanticEntityResolution.NEEDS_REVIEW
            reason = (
                "no exact registry hit, but one or more reviewed entities are similar; "
                "similarity may not merge concepts, so a person decides"
            )
        elif len(entry.passages) < MIN_EVIDENCE_FOR_NEW_ENTITY:
            resolution = SemanticEntityResolution.NEEDS_REVIEW
            reason = (
                f"proposed from {len(entry.passages)} mantra(s); a concept seen once is "
                "usually a phrasing rather than a reusable entity"
            )
        else:
            resolution = SemanticEntityResolution.ACCEPTED_NEW_ENTITY
            reason = "no registry hit, nothing similar, and proposed from several mantras"
        resolved.append(
            SemanticEntityCandidate(
                candidate_id=key,
                entity_type=entry.entity_type,
                preferred_label=entry.preferred_label,
                normalized_label=entry.normalized_label,
                description=entry.description,
                aliases=sorted(entry.aliases),
                source_passage_keys=sorted(entry.passages),
                evidence_count=len(entry.passages),
                created_by_model=model,
                prompt_version=prompt_version,
                ontology_version=ontology_version,
                resolution=resolution,
                matched_entity_key=matched,
                review_candidate_keys=similar,
                resolution_reason=reason,
            )
        )
    return resolved


@dataclass(frozen=True)
class NormalizationGroup:
    """Candidates a reviewer should look at together. A queue item, not a decision."""

    entity_type: SemanticNodeType
    members: tuple[str, ...]
    labels: tuple[str, ...]
    reason: str


def normalization_queue(candidates: list[SemanticEntityCandidate]) -> list[NormalizationGroup]:
    """Group candidates that a person should adjudicate as possible duplicates.

    Grouping is by character similarity within one node type, and the output is a queue.
    It merges nothing, writes no alias, and creates no entity. Two labels appearing in a
    group is a question ("are these the same concept?"), never an answer.
    """
    by_type: dict[SemanticNodeType, list[SemanticEntityCandidate]] = {}
    for candidate in candidates:
        by_type.setdefault(candidate.entity_type, []).append(candidate)

    groups: list[NormalizationGroup] = []
    for node_type, members in sorted(by_type.items()):
        ordered = sorted(members, key=lambda item: item.candidate_id)
        assigned: dict[str, int] = {}
        clusters: list[list[SemanticEntityCandidate]] = []
        for candidate in ordered:
            target: int | None = None
            for index, cluster in enumerate(clusters):
                if any(
                    SequenceMatcher(
                        None, other.normalized_label, candidate.normalized_label
                    ).ratio()
                    >= REVIEW_SIMILARITY
                    for other in cluster
                ):
                    target = index
                    break
            if target is None:
                clusters.append([candidate])
                assigned[candidate.candidate_id] = len(clusters) - 1
            else:
                clusters[target].append(candidate)
                assigned[candidate.candidate_id] = target
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            groups.append(
                NormalizationGroup(
                    entity_type=node_type,
                    members=tuple(item.candidate_id for item in cluster),
                    labels=tuple(item.preferred_label for item in cluster),
                    reason=(
                        f"{len(cluster)} candidate labels of type {node_type.value} are "
                        f"within {REVIEW_SIMILARITY:.2f} character similarity of each other"
                    ),
                )
            )
    return groups
