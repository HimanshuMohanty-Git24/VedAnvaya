"""Merge the V2 entity fragments into one registry, in one alias namespace.

The V1 lexicon lives in ``data/registry/concepts.yaml`` and V2 adds to it. The obvious
implementation -- keep the new entities in their own file and load both -- is the one
mistake this module exists to avoid.

``load_concepts`` refuses an alias claimed by two entities, and that refusal is what makes
the matcher's ``dict[alias] -> entity`` lookup correct instead of order-dependent. But the
check runs *per file*. Two registries means two namespaces, so ``takman`` could be claimed
by a ``CONDITION`` in one and by ``YAKSMA-DISEASE`` in the other, both loads would pass,
and which entity a passage got would be decided by whichever loader ran second. That is a
silent, order-dependent misassignment: precisely the class of bug the single-namespace
check was written to make impossible.

So the fragments are merged into one document first and validated once. The merged file is
written to ``data/domain/`` as a build artifact rather than back into
``data/registry/concepts.yaml``, for two reasons: the V1 registry carries hand-authored
explanatory comments that a YAML round-trip would delete, and rewriting a whole file on
Windows to add entries to a list is how line endings get silently converted across 1,287
lines. The original is read, never written.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final

import yaml

from vedagraph.domain.ontology import ALL_NODE_TYPE_NAMES, DOMAIN_MODEL_VERSION
from vedagraph.enrich.concepts import (
    CONCEPT_REGISTRY_PATH,
    ConceptRegistryError,
    fold_alias,
    load_concepts,
)
from vedagraph.enrich.records import ConceptRow

DOMAIN_DIR: Final = pathlib.Path("data") / "domain" / "vedagraph_domain_v2"

#: Where the merged registry is written. A build artifact: regenerable, and never the
#: place a person edits.
MERGED_REGISTRY_PATH: Final = DOMAIN_DIR / "domain_registry.yaml"

#: Fragment files, in merge order. Missing files are skipped and reported, so the build
#: runs before every fragment is authored.
FRAGMENT_FILES: Final[tuple[pathlib.Path, ...]] = (
    DOMAIN_DIR / "domain_entities_material.yaml",
    DOMAIN_DIR / "domain_entities_concern.yaml",
)


#: V2 retypes of V1 entities, applied during the merge with the reason recorded.
#:
#: An overlay rather than an edit to ``concepts.yaml``, for the same reason as everywhere
#: else in this package: the V1 artifact must stay reproducible from the V1 registry. The
#: narrow type always implies the broad one -- ``METAL`` carries ``Substance`` -- so a
#: retype can only add a way to find the entity, never remove one.
NODE_TYPE_OVERRIDES: Final[dict[str, tuple[str, str]]] = {
    "VG:CONCEPT:HIRANYA-GOLD": (
        "METAL",
        "V1 typed gold as SUBSTANCE, which was reasonable before METAL existed. It left "
        "`MATCH (:Metal)` answering 'which metals occur in each Veda' without the "
        "commonest metal in the corpus. METAL also carries Substance, so nothing is lost.",
    ),
}


@dataclass
class MergeReport:
    """What came from where, and what was refused."""

    base_entities: int = 0
    fragment_entities: dict[str, int] = field(default_factory=dict)
    missing_fragments: list[str] = field(default_factory=list)
    merged_entities: int = 0
    duplicate_ids: list[str] = field(default_factory=list)
    alias_collisions: list[str] = field(default_factory=list)
    by_node_type: dict[str, int] = field(default_factory=dict)
    retyped: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.duplicate_ids and not self.alias_collisions

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_entities": self.base_entities,
            "fragment_entities": dict(sorted(self.fragment_entities.items())),
            "missing_fragments": sorted(self.missing_fragments),
            "merged_entities": self.merged_entities,
            "duplicate_ids": sorted(self.duplicate_ids),
            "alias_collisions": sorted(self.alias_collisions),
            "by_node_type": dict(sorted(self.by_node_type.items())),
            "retyped": self.retyped,
            "clean": self.clean,
        }


def _read(path: pathlib.Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ConceptRegistryError(f"{path}: expected a mapping at the top level")
    return parsed


def merge_registry(project_root: pathlib.Path) -> MergeReport:
    """Write the merged registry, refusing to write one that would not load.

    Collisions are detected here rather than left to ``load_concepts`` for one reason: the
    error a merge can raise names the two *files* involved, which is what a person needs
    in order to fix it. By the time the merged document is loaded, that information is
    gone.
    """
    report = MergeReport()
    base = _read(project_root / CONCEPT_REGISTRY_PATH)
    base_entries = list(base.get("concepts") or [])
    report.base_entities = len(base_entries)

    merged: list[dict[str, Any]] = list(base_entries)
    origin: dict[str, str] = {
        str(entry.get("concept_id")): str(CONCEPT_REGISTRY_PATH) for entry in base_entries
    }
    claimed: dict[str, tuple[str, str]] = {}
    for entry in base_entries:
        for alias in entry.get("aliases_sa") or []:
            claimed[fold_alias(str(alias))] = (
                str(entry.get("concept_id")),
                str(CONCEPT_REGISTRY_PATH),
            )

    for relative in FRAGMENT_FILES:
        path = project_root / relative
        if not path.exists():
            report.missing_fragments.append(str(relative))
            continue
        entries = list(_read(path).get("concepts") or [])
        report.fragment_entities[str(relative)] = len(entries)
        for entry in entries:
            concept_id = str(entry.get("concept_id", ""))
            if concept_id in origin:
                report.duplicate_ids.append(
                    f"{concept_id} in both {origin[concept_id]} and {relative}"
                )
                continue
            collided = False
            for alias in entry.get("aliases_sa") or []:
                folded = fold_alias(str(alias))
                owner = claimed.get(folded)
                if owner is not None and owner[0] != concept_id:
                    report.alias_collisions.append(
                        f"{alias!r} claimed by {concept_id} ({relative}) and by "
                        f"{owner[0]} ({owner[1]})"
                    )
                    collided = True
            if collided:
                continue
            for alias in entry.get("aliases_sa") or []:
                claimed[fold_alias(str(alias))] = (concept_id, str(relative))
            origin[concept_id] = str(relative)
            merged.append(entry)

    if not report.clean:
        raise ConceptRegistryError(
            "refusing to write a registry that would not load:\n  "
            + "\n  ".join(sorted(report.duplicate_ids + report.alias_collisions))
        )

    for entry in merged:
        override = NODE_TYPE_OVERRIDES.get(str(entry.get("concept_id")))
        if override is not None:
            node_type, reason = override
            if entry.get("node_type") != node_type:
                report.retyped[str(entry["concept_id"])] = {
                    "from": entry.get("node_type"),
                    "to": node_type,
                    "reason": reason,
                }
                entry["node_type"] = node_type

    merged.sort(key=lambda entry: str(entry.get("concept_id")))
    report.merged_entities = len(merged)
    for entry in merged:
        node_type = str(entry.get("node_type", "?"))
        report.by_node_type[node_type] = report.by_node_type.get(node_type, 0) + 1

    document = {
        "policy_version": base.get("policy_version"),
        "domain_model_version": DOMAIN_MODEL_VERSION,
        "ambiguous_aliases": base.get("ambiguous_aliases") or [],
        "concepts": merged,
    }
    target = project_root / MERGED_REGISTRY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# GENERATED by vedagraph.domain.registry.merge_registry -- do not edit.\n"
        "#\n"
        f"# {CONCEPT_REGISTRY_PATH.as_posix()} plus the V2 fragments, merged into a single\n"
        "# alias namespace so that an alias claimed by two entities is a load failure\n"
        "# rather than an assignment decided by which file was read last.\n"
        "#\n"
        "# Edit the fragments or the base registry, then re-run the domain build.\n"
    )
    body = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100)
    # Explicit LF: the base registry is LF throughout and a Windows default would rewrite
    # every line of the artifact as CRLF, which makes a one-entity change look total.
    target.write_text(header + body, encoding="utf-8", newline="\n")
    return report


def load_domain_entities(project_root: pathlib.Path) -> tuple[ConceptRow, ...]:
    """Load and fully validate the merged registry under the V2 type vocabulary."""
    return load_concepts(
        project_root,
        allowed_node_types=ALL_NODE_TYPE_NAMES,
        registry_path=MERGED_REGISTRY_PATH,
    )


def entities_by_node_type(entities: Sequence[ConceptRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.node_type] = counts.get(entity.node_type, 0) + 1
    return dict(sorted(counts.items()))
