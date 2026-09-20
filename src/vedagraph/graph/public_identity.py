"""Stable publication identity shared by API and offline consumers.

Existing published identifiers are retained verbatim. The deterministic semantic
layer already has a persisted assertion_key; expose that key in its own namespace,
never its contextual passage canonical_key. No graph identity is rewritten and no
ordinal, text, timestamp, or Neo4j element id is used to mint a new identity here.
"""

from typing import Any, Mapping

ASSERTION_PREFIX = "semantic-assertion:"
ID_PROPERTIES = (
    "assertion_id", "entity_key", "canonical_key", "formula_id", "concept_id",
    "ascription_id", "metric_id", "step_key", "group_id", "family_id",
    "family_key", "group_key", "axis_key", "epithet_key", "claim_id", "work_id",
    "lemma", "predicate",
)


def public_id(properties: Mapping[str, Any]) -> str | None:
    """Promote a persisted assertion key, otherwise preserve the published id."""
    assertion_id = properties.get("assertion_id")
    if isinstance(assertion_id, str) and assertion_id:
        return assertion_id
    key = properties.get("assertion_key")
    if isinstance(key, str) and key:
        return ASSERTION_PREFIX + key
    for name in ID_PROPERTIES:
        value = properties.get(name)
        if isinstance(value, str) and value:
            return value
    return None


def public_id_cypher(variable: str) -> str:
    """Cypher equivalent of public_id, including empty-string handling."""
    def value(key: str) -> str:
        prop = f"{variable}.{key}"
        return f"CASE WHEN {prop} <> '' THEN {prop} END"

    values = [value("assertion_id")]
    values.append(
        f"CASE WHEN {variable}.assertion_key <> '' "
        f"THEN '{ASSERTION_PREFIX}' + {variable}.assertion_key END"
    )
    values.extend(value(key) for key in ID_PROPERTIES if key != "assertion_id")
    return "coalesce(" + ", ".join(values) + ")"
