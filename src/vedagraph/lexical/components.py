"""Reviewed composite-Devatā decomposition into ``HAS_COMPONENT`` edges.

This is the one place in the layer where the provenance class is ``HUMAN_REVIEWED``
rather than ``DETERMINISTIC_DERIVED``: nothing here is derived from the data at all. The
build reads ``data/registry/devata_components.yaml``, checks that every named entity
exists, and emits an edge only for rows a person marked ``ACCEPTED``.

There is no fallback path. A composite with no reviewed row produces no components, and
a group deity is never expanded into the set of its supposed members.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from vedagraph.identity import uuid_for_urn
from vedagraph.models.enums import ReviewStatus
from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.models.lexical import ComponentAssertion

COMPONENT_FILE = "devata_components.yaml"
COMPONENT_POLICY_VERSION = "rigveda-devata-component-policy-v1"


def load_component_assertions(
    registry_root: Path,
    *,
    entities: dict[str, KnowledgeEntity],
) -> list[ComponentAssertion]:
    """Read the reviewed mapping. Only ``ACCEPTED`` rows produce assertions."""
    path = registry_root / COMPONENT_FILE
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    declared = str(document.get("policy_version", ""))
    if declared != COMPONENT_POLICY_VERSION:
        raise ValueError(
            f"{path} declares policy_version {declared!r}, expected {COMPONENT_POLICY_VERSION!r}"
        )

    assertions: list[ComponentAssertion] = []
    for row in document.get("components", []):
        composite_key = str(row["composite_entity_id"])
        composite = entities.get(composite_key)
        if composite is None:
            raise ValueError(f"{path}: unknown composite entity {composite_key}")
        status = ReviewStatus(row["review_status"])
        component_keys = [str(item) for item in row.get("component_entity_ids", [])]
        for component_key in component_keys:
            if component_key not in entities:
                raise ValueError(f"{path}: {composite_key} names unknown component {component_key}")
        if status is not ReviewStatus.ACCEPTED:
            continue
        if not component_keys:
            raise ValueError(f"{path}: {composite_key} is ACCEPTED but lists no components")
        for sequence, component_key in enumerate(component_keys, start=1):
            urn = (
                "urn:vedagraph:assertion:has_component:"
                f"{composite_key.lower()}:{component_key.lower()}"
            )
            assertions.append(
                ComponentAssertion(
                    assertion_id=uuid_for_urn(urn),
                    subject_key=composite_key,
                    subject_id=composite.entity_id,
                    object_key=component_key,
                    object_id=entities[component_key].entity_id,
                    component_sequence=sequence,
                    evidence=str(row["evidence"]),
                    review_status=status,
                    notes=str(row["notes"]) if row.get("notes") else None,
                )
            )
    return sorted(assertions, key=lambda item: (item.subject_key, item.component_sequence))
