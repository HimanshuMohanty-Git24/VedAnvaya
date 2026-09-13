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

from vedagraph.domain.ontology import (
    ALL_NODE_TYPE_NAMES,
    CONDITION_KINDS,
    DOMAIN_MODEL_VERSION,
)
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
    # V3. Merge order matters only for reporting: the loader refuses a duplicate id or a
    # folded alias claimed twice rather than letting a later fragment win.
    DOMAIN_DIR / "domain_entities_ritual_v3.yaml",
    DOMAIN_DIR / "domain_entities_concern_v3.yaml",
)


#: V2 retypes of V1 entities, applied during the merge with the reason recorded.
#:
#: An overlay rather than an edit to ``concepts.yaml``, for the same reason as everywhere
#: else in this package: the V1 artifact must stay reproducible from the V1 registry. The
#: narrow type always implies the broad one -- ``METAL`` carries ``Substance`` -- so a
#: retype can only add a way to find the entity, never remove one.
#: Base entities a V3 fragment **replaces** rather than sits beside, with the reason.
#:
#: Merging is the default and superseding is the exception, because superseding drops a
#: hand-authored entity and that must never happen by accident. So it is declared here in
#: code, not inferred from the data: the merge honours exactly this list and refuses
#: anything else that collides.
#:
#: The one entry is the case that forced the mechanism to exist. ``YAKSMA-DISEASE`` had
#: four distinct afflictions folded into a single ``State``-labelled node -- *takman*
#: (the Atharvaveda's specific fever, with its own hymns), *yakṣma* (consumption),
#: *amīvā* (general affliction) and *rapas* (bodily hurt) -- and ``State`` accepts no
#: concern predicate at all. Measured against the live graph: 15 of 33 fever mantras
#: arrived labelled "disease", 8 arrived nowhere, and **none carried an affliction edge**,
#: so "what does the Atharvaveda say about fever?" was unanswerable. The four are now
#: separate ``Condition`` entities and the base entry's alias set claims six of their
#: forms, so a merge raises six collisions and is correctly refused. Replacing it is the
#: only honest resolution: the old entity was not a coarser version of the new ones, it
#: was a conflation of them.
SUPERSEDED_BY_FRAGMENT: Final[dict[str, str]] = {
    "VG:CONCEPT:YAKSMA-DISEASE": (
        "Conflated takman, yaksma, amiva and rapas into one STATE-typed node that no "
        "concern predicate could reach. Split into four CONDITION entities by "
        "domain_entities_concern_v3.yaml, which claims six of this entry's aliases. Two "
        "corpus-internal witnesses justify the split rather than a retype: AVS 5.4.9 and "
        "5.30.16 name takman and yaksma contrastively in one line, and the Anukramani "
        "ascribes AVS 5.22 as takmanasanadevatyam, distinct from its yaksmanasana- "
        "ascriptions."
    ),
}


NODE_TYPE_OVERRIDES: Final[dict[str, tuple[str, str]]] = {
    # ---- V3 retypes, each declared by the fragment that needs it ---------------------
    # A predicate can only reach an entity whose label is in its declared range, so a
    # mis-typed entity is not a cosmetic problem: it makes a whole question unanswerable
    # and the failure is silent, because the rows simply do not match.
    "VG:CONCEPT:AYUDHA-WEAPON": (
        "WEAPON",
        "Typed OBJECT, so `MATCH (:Weapon)` returned only bowstring, noose and axe and "
        "the corpus's principal weapon word was invisible to the question the Weapon "
        "label exists to answer. WEAPON carries Object, so nothing is lost.",
    ),
    "VG:CONCEPT:VAJRA-THUNDERBOLT": (
        "WEAPON",
        "As AYUDHA-WEAPON. Indra's vajra is the single most-cited weapon in the corpus "
        "and was not reachable as one.",
    ),
    "VG:CONCEPT:RAKSAS-DEMON": (
        "CONDITION",
        "Typed CONCEPT, which is outside PROTECTS_FROM's declared range, so the demon "
        "nobody can be protected from was a modelling artefact rather than a finding. "
        "CONDITION follows the V1 precedent already used for DURNAMAN and KRTYA, which "
        "are hostile agents typed as conditions for exactly this reason.",
    ),
    "VG:CONCEPT:YAKSMA-DISEASE": (
        "CONDITION",
        "Typed STATE, which accepts no concern predicate at all. This is the node that "
        "had folded takman, yaksma, amiva and rapah into one: 15 of 33 fever mantras "
        "arrived labelled 'disease', 8 arrived nowhere, and none carried an affliction "
        "edge. The four are split into separate Condition entities by "
        "domain_entities_concern_v3.yaml; this retype is what lets any of them carry an "
        "edge.",
    ),
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
    #: Base entities a fragment replaced, with the reason. Non-empty is normal; a
    #: *silent* replacement would not be.
    superseded: dict[str, str] = field(default_factory=dict)

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
            "superseded": dict(sorted(self.superseded.items())),
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

    # Superseded base entries are dropped before anything else, so their aliases never
    # enter the claim table and the fragment that replaces them does not read as a
    # collision. Reported, so a dropped hand-authored entity is visible in the merge
    # report rather than only in this constant.
    kept_base = [
        entry
        for entry in base_entries
        if str(entry.get("concept_id")) not in SUPERSEDED_BY_FRAGMENT
    ]
    report.superseded = {
        str(entry.get("concept_id")): SUPERSEDED_BY_FRAGMENT[str(entry.get("concept_id"))]
        for entry in base_entries
        if str(entry.get("concept_id")) in SUPERSEDED_BY_FRAGMENT
    }
    declared_but_absent = sorted(set(SUPERSEDED_BY_FRAGMENT) - set(report.superseded))
    if declared_but_absent:
        raise ConceptRegistryError(
            "SUPERSEDED_BY_FRAGMENT names entities the base registry does not contain, "
            "so the supersede would silently do nothing: " + ", ".join(declared_but_absent)
        )

    merged: list[dict[str, Any]] = list(kept_base)
    origin: dict[str, str] = {
        str(entry.get("concept_id")): str(CONCEPT_REGISTRY_PATH) for entry in kept_base
    }
    claimed: dict[str, tuple[str, str]] = {}
    for entry in kept_base:
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
    rows = load_concepts(
        project_root,
        allowed_node_types=ALL_NODE_TYPE_NAMES,
        registry_path=MERGED_REGISTRY_PATH,
    )
    _require_condition_kinds(rows)
    return rows


def _require_condition_kinds(rows: Sequence[ConceptRow]) -> None:
    """Every ``CONDITION`` must declare a ``condition_kind``, and it must be a real one.

    Checked here rather than in :func:`vedagraph.enrich.concepts.load_concepts` because
    this is the first point at which an entity's type is final. ``RAKSAS-DEMON`` is
    authored ``node_type: CONCEPT`` in the base registry and retyped to ``CONDITION`` by
    :data:`NODE_TYPE_OVERRIDES` during the merge, so a check against the authored type
    would wave through the demon -- the single entity whose misclassification made
    "which diseases does the corpus name?" answer with a demon in the first place.

    There is deliberately no default and no ``UNSPECIFIED`` to fall back on, so a new
    condition added without a kind fails the build instead of landing in a bucket. See
    :class:`vedagraph.domain.ontology.ConditionKind` for why that value does not exist.
    """
    missing: list[str] = []
    invalid: list[str] = []
    for row in rows:
        if row.node_type != "CONDITION":
            if row.condition_kind:
                invalid.append(
                    f"{row.concept_id} is {row.node_type}, not CONDITION, but declares "
                    f"condition_kind={row.condition_kind!r}"
                )
            continue
        if not row.condition_kind:
            missing.append(row.concept_id)
        elif row.condition_kind not in CONDITION_KINDS:
            invalid.append(
                f"{row.concept_id}: condition_kind={row.condition_kind!r} is not one of "
                f"{sorted(CONDITION_KINDS)}"
            )
    problems = [f"{cid}: CONDITION with no condition_kind" for cid in sorted(missing)]
    problems.extend(sorted(invalid))
    if problems:
        raise ConceptRegistryError("condition_kind contract violated:\n  " + "\n  ".join(problems))


def entities_by_node_type(entities: Sequence[ConceptRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.node_type] = counts.get(entity.node_type, 0) + 1
    return dict(sorted(counts.items()))
