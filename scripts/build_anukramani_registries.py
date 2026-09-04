"""Generate the canonical Ṛṣi, Devatā and Chandas registries from pinned artifacts.

Run this when the pinned Anukramaṇī artifacts or the reviewed alias file change. It is
deterministic and idempotent: the same artifacts and aliases produce byte-identical
registry files.

The generator proposes; it does not decide. It never merges two labels on similarity —
where two labels collide under the readable ASCII fold, both keys are re-derived with
the collision-breaking fold so that the two entities stay separate and both keys stay
stable. Deliberate identifications live in ``data/registry/anukramani_aliases.yaml``.

Devatā subtypes stay ``UNKNOWN`` unless the source paper itself classifies the label.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import yaml

from vedagraph.ingest.adapters import WSC2023AnukramaniAdapter
from vedagraph.knowledge.normalize import ascii_key, distinct_key, normalize_label
from vedagraph.knowledge.registry import REGISTRY_FILES, entity_key_for, load_aliases
from vedagraph.models.enums import AnukramaniField, DevataSubtype, KnowledgeEntityType
from vedagraph.models.knowledge import FIELD_PREDICATE, PREDICATE_ENTITY_TYPE

ARTIFACTS = Path("data/derived/wsc2023_anukramani_artifacts.json")
REGISTRY_ROOT = Path("data/registry")

# The only classifications the WSC2023 paper itself states. Everything else is UNKNOWN.
PAPER_EVIDENCE = "Classified in Akavarapu and Bhattacharya (2023), section 2.1."
DEVATA_SUBTYPES: dict[str, tuple[DevataSubtype, str]] = {
    "indrāgnī": (DevataSubtype.PAIR, f"Named as a dual of Indra and Agni. {PAPER_EVIDENCE}"),
    "mitrāvaruṇau": (
        DevataSubtype.PAIR,
        f"Named as a dual that is deliberately not decomposed into Mitra and Varuṇa. "
        f"{PAPER_EVIDENCE}",
    ),
    "viśvedevāḥ": (
        DevataSubtype.GROUP,
        f"Named as a designated group of devatās. {PAPER_EVIDENCE}",
    ),
    "ādityāḥ": (DevataSubtype.GROUP, f"Named as a designated group of devatās. {PAPER_EVIDENCE}"),
    "dānastutiḥ": (
        DevataSubtype.ABSTRACT,
        f"Praise of a patron, labelled without the patron's name; the paper calls it an "
        f"abstract class rather than a deity. {PAPER_EVIDENCE}",
    ),
}


def collect_labels() -> dict[KnowledgeEntityType, dict[str, list[str]]]:
    adapter = WSC2023AnukramaniAdapter()
    artifacts = json.loads(ARTIFACTS.read_text(encoding="utf-8"))
    labels: dict[KnowledgeEntityType, dict[str, list[str]]] = {
        entity_type: defaultdict(list) for entity_type in KnowledgeEntityType
    }
    for artifact in sorted(artifacts, key=lambda item: int(item["mandala"])):
        records = adapter.parse_anukramani(
            Path(artifact["snapshot_path"]),
            snapshot_id=str(artifact["snapshot_id"]),
            source_artifact_id=str(artifact["artifact_id"]),
            mandala=int(artifact["mandala"]),
        )
        for record in records:
            for segment in record.segments:
                entity_type = PREDICATE_ENTITY_TYPE[FIELD_PREDICATE[AnukramaniField(segment.field)]]
                labels[entity_type][normalize_label(segment.raw_value)].append(segment.raw_value)
    return {
        entity_type: {label: sorted(set(raw)) for label, raw in sorted(mapping.items())}
        for entity_type, mapping in labels.items()
    }


def assign_keys(entity_type: KnowledgeEntityType, labels: list[str]) -> dict[str, str]:
    """Readable ASCII keys, with every member of a colliding group re-derived."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for label in labels:
        grouped[ascii_key(label)].append(label)
    keys: dict[str, str] = {}
    for slug, members in grouped.items():
        if len(members) == 1:
            keys[members[0]] = entity_key_for(entity_type, slug)
            continue
        for label in members:
            keys[label] = entity_key_for(entity_type, distinct_key(label))
    duplicates = {key for key in keys.values() if list(keys.values()).count(key) > 1}
    if duplicates:
        raise ValueError(f"unresolved {entity_type} key collision: {sorted(duplicates)}")
    return keys


def main() -> None:
    aliases = load_aliases(REGISTRY_ROOT)
    alias_targets = {
        (alias.entity_type, normalize_label(alias.alias)): normalize_label(alias.canonical)
        for alias in aliases
    }
    collected = collect_labels()
    for entity_type, raw_labels in collected.items():
        canonical: dict[str, list[str]] = defaultdict(list)
        for label, raws in raw_labels.items():
            target = alias_targets.get((entity_type, label), label)
            canonical[target].extend(raws)
        for target in canonical:
            if target not in raw_labels:
                raise ValueError(
                    f"alias target {target!r} does not occur in the {entity_type} data"
                )
        keys = assign_keys(entity_type, sorted(canonical))
        entities = []
        for label in sorted(canonical):
            subtype, note = (
                DEVATA_SUBTYPES.get(label, (DevataSubtype.UNKNOWN, None))
                if entity_type is KnowledgeEntityType.DEVATA
                else (None, None)
            )
            entry: dict[str, object] = {
                "entity_key": keys[label],
                "entity_type": entity_type.value,
                "preferred_label": label,
            }
            if subtype is not None:
                entry["devata_subtype"] = subtype.value
            if note:
                entry["notes"] = note
            entities.append(entry)
        path = REGISTRY_ROOT / REGISTRY_FILES[entity_type]
        header = (
            f"# Canonical {entity_type.value} registry, generated by\n"
            "# scripts/build_anukramani_registries.py from the commit-pinned WSC2023\n"
            "# Anukramaṇī artifacts plus data/registry/anukramani_aliases.yaml.\n"
            "#\n"
            "# preferred_label is the source label, normalized for Unicode form, whitespace\n"
            "# and case only. entity_key is pinned identity: do not recompute it by hand and\n"
            "# do not renumber it when the generator runs again.\n"
        )
        path.write_text(
            header + yaml.safe_dump({"entities": entities}, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )
        print(f"{path}: {len(entities)} entities")


if __name__ == "__main__":
    main()
