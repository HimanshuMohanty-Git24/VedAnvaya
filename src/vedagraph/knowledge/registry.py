"""Canonical entity registries and the deterministic resolution ladder.

The registries under ``data/registry`` are reviewed, version-controlled data. The build
reads them; it never invents an entity, and it never merges two spellings on similarity.
Fuzzy comparison appears in exactly one place — :meth:`EntityResolver.candidates` — and
only to suggest review candidates, never to attach a canonical id.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from vedagraph.identity import entity_identity
from vedagraph.knowledge.normalize import (
    ascii_key,
    composite_parts,
    is_composite_label,
    normalize_label,
)
from vedagraph.models.core import SCHEMA_VERSION, VGModel
from vedagraph.models.enums import (
    AliasType,
    DevataSubtype,
    KnowledgeEntityType,
    ResolutionStatus,
)
from vedagraph.models.knowledge import EntityAlias, KnowledgeEntity

RESOLUTION_POLICY_VERSION = "anukramani-entity-resolution-v1"

REGISTRY_FILES: dict[KnowledgeEntityType, str] = {
    KnowledgeEntityType.RISHI: "rishis.yaml",
    KnowledgeEntityType.DEVATA: "devatas.yaml",
    KnowledgeEntityType.CHANDAS: "chandas.yaml",
}
ALIAS_FILE = "anukramani_aliases.yaml"

_KEY_PREFIX = {
    KnowledgeEntityType.RISHI: "RISHI",
    KnowledgeEntityType.DEVATA: "DEVATA",
    KnowledgeEntityType.CHANDAS: "CHANDAS",
}


class EntityRegistryEntry(VGModel):
    """One reviewed registry row. ``entity_key`` is pinned, never recomputed."""

    entity_key: str = Field(pattern=r"^VG:(RISHI|DEVATA|CHANDAS):[A-Z0-9-]+$")
    entity_type: KnowledgeEntityType
    preferred_label: str = Field(min_length=1)
    devanagari: str | None = None
    devata_subtype: DevataSubtype | None = None
    notes: str | None = None
    schema_version: str = SCHEMA_VERSION


class AliasRegistryEntry(VGModel):
    """One reviewed statement that a source spelling names a registered entity."""

    entity_type: KnowledgeEntityType
    alias: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    alias_type: AliasType
    evidence: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class Resolution:
    """Outcome of resolving one raw label."""

    normalized_label: str
    canonical_label: str
    status: ResolutionStatus
    entity_key: str | None
    alias_type: AliasType | None
    reason: str


def load_entity_registry(
    entity_type: KnowledgeEntityType, *, root: Path = Path("data/registry")
) -> list[EntityRegistryEntry]:
    path = root / REGISTRY_FILES[entity_type]
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("entities"), list):
        raise ValueError(f"{path} must contain an 'entities' list")
    entries = [EntityRegistryEntry.model_validate(item) for item in payload["entities"]]
    for entry in entries:
        if entry.entity_type is not entity_type:
            raise ValueError(f"{path} contains a {entry.entity_type} entry")
    return entries


def load_aliases(root: Path = Path("data/registry")) -> list[AliasRegistryEntry]:
    path = root / ALIAS_FILE
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("aliases"), list):
        raise ValueError(f"{path} must contain an 'aliases' list")
    return [AliasRegistryEntry.model_validate(item) for item in payload["aliases"]]


def entity_key_for(entity_type: KnowledgeEntityType, slug: str) -> str:
    return f"VG:{_KEY_PREFIX[entity_type]}:{slug}"


class EntityResolver:
    """Deterministic label → canonical entity resolution for one entity type."""

    def __init__(
        self,
        entity_type: KnowledgeEntityType,
        entries: list[EntityRegistryEntry],
        aliases: list[AliasRegistryEntry],
    ) -> None:
        self.entity_type = entity_type
        self.entries = sorted(entries, key=lambda entry: entry.entity_key)
        self._by_label: dict[str, EntityRegistryEntry] = {}
        self._by_key: dict[str, EntityRegistryEntry] = {}
        self._by_ascii: dict[str, list[str]] = defaultdict(list)
        for entry in self.entries:
            label = normalize_label(entry.preferred_label)
            if label in self._by_label:
                raise ValueError(f"duplicate preferred_label {label!r} in {entity_type} registry")
            if entry.entity_key in self._by_key:
                raise ValueError(f"duplicate entity_key {entry.entity_key} in {entity_type}")
            self._by_label[label] = entry
            self._by_key[entry.entity_key] = entry
            self._by_ascii[ascii_key(label)].append(entry.entity_key)
        self._aliases: dict[str, AliasRegistryEntry] = {}
        for alias in aliases:
            if alias.entity_type is not entity_type:
                continue
            key = normalize_label(alias.alias)
            if key in self._aliases:
                raise ValueError(f"duplicate alias {key!r} for {entity_type}")
            if key in self._by_label:
                raise ValueError(f"alias {key!r} is also a preferred label for {entity_type}")
            self._aliases[key] = alias

    def resolve(self, raw_label: str) -> Resolution:
        normalized = normalize_label(raw_label)
        alias = self._aliases.get(normalized)
        canonical = normalize_label(alias.canonical) if alias else normalized
        entry = self._by_label.get(canonical)
        if entry is None:
            return Resolution(
                normalized_label=normalized,
                canonical_label=canonical,
                status=ResolutionStatus.NEEDS_REVIEW,
                entity_key=None,
                alias_type=alias.alias_type if alias else None,
                reason=(
                    f"alias target {canonical!r} is not registered"
                    if alias
                    else "label is not registered"
                ),
            )
        if alias is not None:
            status = ResolutionStatus.KNOWN_ALIAS
            reason = f"reviewed {alias.alias_type.value} of {entry.entity_key}"
        elif is_composite_label(canonical):
            status = ResolutionStatus.COMPOSITE_PRESERVED
            reason = "source composite label kept whole; components are not decomposed"
        elif raw_label == canonical:
            status = ResolutionStatus.EXACT
            reason = "raw label matches the registered label byte for byte"
        else:
            status = ResolutionStatus.NORMALIZED_EXACT
            reason = "label matches after Unicode, whitespace and case normalization"
        return Resolution(
            normalized_label=normalized,
            canonical_label=canonical,
            status=status,
            entity_key=entry.entity_key,
            alias_type=alias.alias_type if alias else None,
            reason=reason,
        )

    def candidates(self, label: str) -> list[str]:
        """Review suggestions only. Never used to attach a canonical entity."""
        return sorted(self._by_ascii.get(ascii_key(normalize_label(label)), []))

    def entry(self, entity_key: str) -> EntityRegistryEntry:
        return self._by_key[entity_key]

    def alias_entries(self, entity_key: str) -> list[EntityAlias]:
        entry = self._by_key[entity_key]
        target = normalize_label(entry.preferred_label)
        return [
            EntityAlias(alias=alias.alias, alias_type=alias.alias_type, evidence=alias.evidence)
            for alias in sorted(self._aliases.values(), key=lambda item: item.alias)
            if normalize_label(alias.canonical) == target
        ]

    def build_entities(
        self, source_labels: dict[str, list[str]], occurrences: dict[str, int]
    ) -> list[KnowledgeEntity]:
        """Materialize canonical entity records for this registry."""
        entities: list[KnowledgeEntity] = []
        for entry in self.entries:
            label = normalize_label(entry.preferred_label)
            slug = entry.entity_key.split(":")[-1]
            key, urn, entity_id = entity_identity(_KEY_PREFIX[self.entity_type], slug)
            if key != entry.entity_key:
                raise ValueError(f"registry key {entry.entity_key} is not a valid entity key")
            composite = is_composite_label(label)
            entities.append(
                KnowledgeEntity(
                    entity_id=entity_id,
                    entity_key=entry.entity_key,
                    canonical_urn=urn,
                    entity_type=self.entity_type,
                    preferred_label=entry.preferred_label,
                    preferred_label_iast=entry.preferred_label,
                    devanagari=entry.devanagari,
                    aliases=self.alias_entries(entry.entity_key),
                    source_labels=sorted(source_labels.get(entry.entity_key, [])),
                    is_composite=composite,
                    composite_parts=composite_parts(label) if composite else [],
                    devata_subtype=entry.devata_subtype,
                    resolution_status=(
                        ResolutionStatus.COMPOSITE_PRESERVED
                        if composite
                        else ResolutionStatus.EXACT
                    ),
                    provenance=["WSC2023.RV.ANUKRAMANI"],
                    occurrence_count=occurrences.get(entry.entity_key, 0),
                    notes=entry.notes,
                )
            )
        return entities


def load_resolvers(root: Path = Path("data/registry")) -> dict[KnowledgeEntityType, EntityResolver]:
    aliases = load_aliases(root)
    return {
        entity_type: EntityResolver(
            entity_type, load_entity_registry(entity_type, root=root), aliases
        )
        for entity_type in KnowledgeEntityType
    }
