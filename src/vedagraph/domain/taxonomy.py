"""The Devatā overlay: multi-axial roles, structure, labels, epithets and groups.

An overlay rather than an edit, for two reasons that point the same way.

``data/registry/devatas.yaml`` is generated from commit-pinned Anukramaṇī artifacts, and
its own header says the ``entity_key`` values are pinned identity that must not be
recomputed by hand. Editing curated roles into it would put hand-authored judgement in a
file whose next regeneration would silently discard it. So identity stays in the generated
registry and interpretation lives here, joined on the pinned key -- which
:func:`load_taxonomy` verifies resolves, because an overlay keyed to an entity that does
not exist is a silent no-op rather than an error.

The model itself replaces one enum with two orthogonal ones, because the single
``devata_subtype`` field was forcing a false choice. Agni had to be filed as *either* a
deity *or* a natural phenomenon *or* a ritual object; the correct answer is that the corpus
treats Agni as all three, and a field that cannot say so will be ``UNKNOWN`` on 97.7% of
its rows, which is what it was.

:class:`~vedagraph.domain.ontology.DevataStructure` keeps the part the label itself
settles -- a dual is a dual, a plural naming a class is a group, a label built on
``dānastuti`` is the praise of a patron. That axis never had the collapsing problem because
it is a fact about the label rather than a reading of the deity.

:class:`~vedagraph.domain.ontology.DeityAxis` takes the part that does: a set, not a
choice. It is explicitly *functional* -- what the corpus does with a deity -- and not a
pantheon-wide domain assignment, because ``IS_GOD_OF`` is a predicate the frozen semantic
ontology refuses by name on the grounds that systematised domain theology is largely later
than these texts. ``UNSPECIFIED`` is a first-class value and is expected to be common: a
justified UNSPECIFIED is worth more than an invented axis, and the scorecard counts it as
unclassified rather than folding it into a coverage figure.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

import yaml

from vedagraph.domain.ontology import (
    DOMAIN_MODEL_VERSION,
    LABEL_DEITY_AXIS,
    LABEL_DEITY_GROUP,
    LABEL_EPITHET,
    DeityAxis,
    DevataStructure,
    is_meaningful_label,
)

TAXONOMY_PATH: Final = (
    pathlib.Path("data") / "domain" / "vedagraph_domain_v2" / "devata_taxonomy.yaml"
)
DEVATA_REGISTRY_PATH: Final = pathlib.Path("data") / "registry" / "devatas.yaml"


class TaxonomyError(ValueError):
    """The overlay is not loadable as written."""


@dataclass(frozen=True)
class Epithet:
    """One attested by-name of a deity."""

    iast: str
    english: str

    @property
    def epithet_key(self) -> str:
        return f"VG:EPITHET:{self.iast.upper().replace(' ', '-')}"

    def as_row(self) -> dict[str, Any]:
        return {
            "epithet_key": self.epithet_key,
            "label_iast": self.iast,
            "label_en": self.english,
            "display_label": f"{self.iast} ({self.english})" if self.english else self.iast,
            "display_type": LABEL_EPITHET,
            "domain_model_version": DOMAIN_MODEL_VERSION,
        }


@dataclass(frozen=True)
class DevataTaxonomyEntry:
    """The curated overlay for one Devatā entity."""

    entity_key: str
    structure: DevataStructure
    axes: tuple[DeityAxis, ...]
    label_iast: str
    label_en: str
    short_description: str
    aliases_iast: tuple[str, ...]
    epithets: tuple[Epithet, ...]
    member_of: tuple[str, ...]
    composed_of: tuple[str, ...]
    curation_note: str
    confidence: str

    @property
    def is_classified(self) -> bool:
        """Whether this entry says anything beyond "we do not know".

        The scorecard's UNKNOWN_TAXONOMY_RATE is the complement of this. Structure alone
        does not count: it is largely mechanical from the label, so counting it as
        classification would let morphology masquerade as scholarship.
        """
        return bool(self.axes) and self.axes != (DeityAxis.UNSPECIFIED,)

    def as_row(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "structure": str(self.structure),
            "axes": [str(axis) for axis in self.axes],
            "axis_count": len(self.axes),
            "is_classified": self.is_classified,
            "label_iast": self.label_iast,
            "label_en": self.label_en,
            "display_label": self.label_en or self.label_iast or self.entity_key,
            "display_type": "Devata",
            "short_description": self.short_description,
            "aliases_iast": list(self.aliases_iast),
            "epithet_count": len(self.epithets),
            "curation_note": self.curation_note,
            "curation_confidence": self.confidence,
            # Set on every deity, not only the 25 that get a full profile. Without it a
            # reader sees "Indra: AV 0" and concludes Indra is absent from the
            # Atharvaveda, when the truth is that the Atharvaveda has no attribution
            # layer at all and 571 of its passages contain the word `indra`. A scope note
            # present on 25 of 214 nodes is a scope note that will be missed.
            # attribution_scope is DELIBERATELY ABSENT from this row. It is derived from the
            # graph by :func:`vedagraph.domain.loader.apply_overlay` immediately after this
            # SET, per GAP-ATTRIBUTION-009's own implementation_dependency: "Derive
            # attribution_scope from the graph at projection time instead of storing a
            # literal, so it cannot outlive the fact it describes."
            #
            # It WAS the literal ["RV"] here, on all 214 nodes. R3 measured it per node and
            # landed 35 as ["RV","AV"] -- and left this literal in place, so the very next
            # rebuild through this overlay would have flattened all 35 back. A stored literal
            # that a mutation has to correct out-of-band is the defect, not the value.
            # The second sentence used to read "means that corpus has no attribution
            # layer", which was false for the Atharvaveda and reached the reader on all 214
            # nodes -- and reached Ask, which passes this string through as the qualifier on
            # an absence, so a false "no attribution layer" became a model-visible
            # justification for a false answer.
            "attribution_scope_note": (
                "attribution_scope names the corpora whose dedications are RESOLVED to this "
                "node. HAS_DEVATA is Rigveda-only, so a zero for SV, YV or AV means this "
                "predicate does not reach that corpus -- NOT that the deity is absent from "
                "it, and NOT that the corpus records no dedication. The Atharvaveda records "
                "its own: 5,385 HAS_DEVATA_ASCRIPTION edges over 4,665 of its 6,590 "
                "passages, 4,816 of them on 4,160 of its 5,839 mantras and the rest on "
                "hymn-level containers, pointing at a :DevataAscription that carries "
                "Whitney's verbatim descriptor rather than a resolved deity. Those two "
                "layers share no label value, by category rather than by coverage. The "
                "bridge between them is BUILT and partial: HAS_DEVATA_DERIVED carries 882 "
                "Atharvavedic dedications over 851 passages for 39 of the 324 descriptors, "
                "resolved from the descriptor's own morphology under Panini 4.2.24 sasya "
                "devata, and the other 285 are refused with a typed reason each rather than "
                "left unprocessed. Those resolved dedications DO raise this figure; an "
                "unresolved descriptor does not, because it names no deity to raise it for. "
                "The Samaveda and Yajurveda carry no dedication layer of any kind, which is "
                "a source block (GAP-ATTRIBUTION-001) and not an unbuilt projection."
            ),
            "domain_model_version": DOMAIN_MODEL_VERSION,
        }


@dataclass
class TaxonomySummary:
    """What the overlay covers, for the scorecard."""

    entries: int = 0
    classified: int = 0
    unspecified_axes: int = 0
    unspecified_structure: int = 0
    registry_entities: int = 0
    missing_from_overlay: tuple[str, ...] = ()
    by_axis: dict[str, int] = field(default_factory=dict)
    by_structure: dict[str, int] = field(default_factory=dict)
    epithets: int = 0
    groups: int = 0
    aliases: int = 0

    @property
    def unknown_taxonomy_rate(self) -> float:
        """Share of registry Devatās with no real functional axis.

        Denominator is the registry, not the overlay, so an entity the overlay simply
        omits counts as unclassified rather than vanishing from the measurement.
        """
        if not self.registry_entities:
            return 0.0
        return round((self.registry_entities - self.classified) / self.registry_entities, 6)

    def as_dict(self) -> dict[str, Any]:
        return {
            "registry_entities": self.registry_entities,
            "overlay_entries": self.entries,
            "classified_with_axes": self.classified,
            "axes_unspecified": self.unspecified_axes,
            "structure_unspecified": self.unspecified_structure,
            "missing_from_overlay": list(self.missing_from_overlay),
            "unknown_taxonomy_rate": self.unknown_taxonomy_rate,
            "by_axis": dict(sorted(self.by_axis.items())),
            "by_structure": dict(sorted(self.by_structure.items())),
            "epithets": self.epithets,
            "deity_groups": self.groups,
            "aliases": self.aliases,
        }


def registry_keys(project_root: pathlib.Path) -> frozenset[str]:
    """Pinned Devatā identities from the generated registry."""
    path = project_root / DEVATA_REGISTRY_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entities = document.get("entities") if isinstance(document, dict) else None
    if not isinstance(entities, list) or not entities:
        raise TaxonomyError(f"{DEVATA_REGISTRY_PATH}: no entities")
    return frozenset(str(entity["entity_key"]) for entity in entities if "entity_key" in entity)


def _strings(entity_key: str, field_name: str, value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TaxonomyError(f"{entity_key}: {field_name} must be a list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TaxonomyError(f"{entity_key}: {field_name} contains an empty entry")
        text = item.strip()
        if text not in out:
            out.append(text)
    return tuple(out)


def _epithets(entity_key: str, value: object) -> tuple[Epithet, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise TaxonomyError(f"{entity_key}: epithets must be a list")
    out: list[Epithet] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TaxonomyError(f"{entity_key}: every epithet must be a mapping")
        iast = str(item.get("iast", "")).strip()
        if not iast:
            raise TaxonomyError(f"{entity_key}: an epithet has no 'iast' form")
        out.append(Epithet(iast=iast, english=str(item.get("en", "") or "").strip()))
    return tuple(out)


def load_taxonomy(
    project_root: pathlib.Path,
) -> tuple[tuple[DevataTaxonomyEntry, ...], TaxonomySummary]:
    """Parse and validate the overlay against the pinned registry.

    Returns empty rather than raising when the file is absent, so the build runs before the
    overlay is authored and reports the gap instead of failing on it.
    """
    known = registry_keys(project_root)
    summary = TaxonomySummary(registry_entities=len(known))
    path = project_root / TAXONOMY_PATH
    if not path.exists():
        summary.missing_from_overlay = tuple(sorted(known))
        return (), summary

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise TaxonomyError(f"{TAXONOMY_PATH}: expected a mapping at the top level")
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise TaxonomyError(f"{TAXONOMY_PATH}: 'entries' must be a non-empty list")

    structures = {str(member) for member in DevataStructure}
    axis_names = {str(member) for member in DeityAxis}
    entries: list[DevataTaxonomyEntry] = []
    seen: set[str] = set()
    groups: set[str] = set()

    for raw in raw_entries:
        if not isinstance(raw, Mapping):
            raise TaxonomyError("every overlay entry must be a mapping")
        entity_key = str(raw.get("entity_key", "")).strip()
        if entity_key not in known:
            raise TaxonomyError(
                f"{entity_key!r} is not in {DEVATA_REGISTRY_PATH}. The overlay joins on "
                "pinned identity; a key that does not resolve is a silent no-op."
            )
        if entity_key in seen:
            raise TaxonomyError(f"duplicate overlay entry for {entity_key}")
        seen.add(entity_key)

        structure = str(raw.get("structure", DevataStructure.UNSPECIFIED))
        if structure not in structures:
            raise TaxonomyError(
                f"{entity_key}: structure {structure!r} is not a DevataStructure. "
                f"Allowed: {', '.join(sorted(structures))}"
            )

        declared = _strings(entity_key, "axes", raw.get("axes")) or (str(DeityAxis.UNSPECIFIED),)
        for axis in declared:
            if axis not in axis_names:
                raise TaxonomyError(
                    f"{entity_key}: axis {axis!r} is not a DeityAxis. "
                    f"Allowed: {', '.join(sorted(axis_names))}"
                )
        if len(declared) > 1 and str(DeityAxis.UNSPECIFIED) in declared:
            raise TaxonomyError(
                f"{entity_key}: UNSPECIFIED cannot be combined with a real axis. "
                "It means 'we did not classify this', not 'and also something else'."
            )

        label_en = str(raw.get("label_en", "") or "").strip()
        if not is_meaningful_label(label_en):
            raise TaxonomyError(
                f"{entity_key}: label_en {label_en!r} is empty or a null sentinel, and it "
                "fills a display slot a reader will see."
            )

        composed_of = _strings(entity_key, "composed_of", raw.get("composed_of"))
        for component in composed_of:
            if component not in known:
                raise TaxonomyError(
                    f"{entity_key}: composed_of names {component!r}, which is not a registry Devata"
                )
        member_of = _strings(entity_key, "member_of", raw.get("member_of"))
        groups.update(member_of)

        entries.append(
            DevataTaxonomyEntry(
                entity_key=entity_key,
                structure=DevataStructure(structure),
                axes=tuple(DeityAxis(axis) for axis in declared),
                label_iast=str(raw.get("label_iast", "") or "").strip(),
                label_en=label_en,
                short_description=" ".join(str(raw.get("short_description", "") or "").split()),
                aliases_iast=_strings(entity_key, "aliases_iast", raw.get("aliases_iast")),
                epithets=_epithets(entity_key, raw.get("epithets")),
                member_of=member_of,
                composed_of=composed_of,
                curation_note=" ".join(str(raw.get("curation_note", "") or "").split()),
                confidence=str(raw.get("confidence", "MEDIUM")),
            )
        )

    summary.entries = len(entries)
    summary.missing_from_overlay = tuple(sorted(known - seen))
    summary.groups = len(groups)
    for entry in entries:
        if entry.is_classified:
            summary.classified += 1
        else:
            summary.unspecified_axes += 1
        if entry.structure is DevataStructure.UNSPECIFIED:
            summary.unspecified_structure += 1
        summary.by_structure[str(entry.structure)] = (
            summary.by_structure.get(str(entry.structure), 0) + 1
        )
        for axis in entry.axes:
            summary.by_axis[str(axis)] = summary.by_axis.get(str(axis), 0) + 1
        summary.epithets += len(entry.epithets)
        summary.aliases += len(entry.aliases_iast)

    return tuple(sorted(entries, key=lambda entry: entry.entity_key)), summary


def registry_label_forms(project_root: pathlib.Path) -> tuple[str, ...]:
    """Every ``preferred_label`` in the generated Devatā registry.

    These are Anukramaṇī citation forms and are already inflected -- ``agniḥ``, not
    ``agni`` -- which is exactly why they matter to the theonym check.
    """
    path = project_root / DEVATA_REGISTRY_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entities = document.get("entities") if isinstance(document, dict) else None
    if not isinstance(entities, list):
        return ()
    return tuple(
        str(entity["preferred_label"])
        for entity in entities
        if isinstance(entity, Mapping) and entity.get("preferred_label")
    )


def devata_name_forms(
    project_root: pathlib.Path, entries: Sequence[DevataTaxonomyEntry]
) -> tuple[str, ...]:
    """Every surface form that is a deity's name, for the theonym-ambiguity check.

    Three sources, and using fewer than all three is a measured mistake rather than a
    theoretical one. Passing only ``label_iast`` -- the uninflected stem -- was the first
    implementation, and it silently disabled the check on the case that matters most: the
    **vocative**. ``agne`` ("O Agni!") does not fold to the stem ``agni``, so 915 mention
    edges asserted that a passage names *fire the element* on the sole evidence of an
    address to the god, and none of them were flagged. Adjudication put the error on that
    one entity at 80.9%.

    That failure is also why an automated gloss screen cannot be trusted here: the English
    gloss list contains "agni" and Griffith prints "Agni", so a translation-based check
    scored the alias 97.5% *correct*. Only the morphology exposes it.
    """
    forms: set[str] = set()
    for entry in entries:
        if entry.label_iast:
            forms.add(entry.label_iast)
        forms.update(entry.aliases_iast)
    forms.update(registry_label_forms(project_root))
    return tuple(sorted(form for form in forms if form))


def axis_row(axis: DeityAxis) -> dict[str, Any]:
    """Node row for one axis. Axes are nodes so a reader can ask "which deities are X"."""
    readable = str(axis).replace("_", " ").lower()
    return {
        "axis_key": f"VG:DEITYAXIS:{axis}",
        "axis": str(axis),
        "display_label": readable,
        "display_type": LABEL_DEITY_AXIS,
        "domain_model_version": DOMAIN_MODEL_VERSION,
    }


def group_row(group_key: str) -> dict[str, Any]:
    """Node row for a named collective of deities (the Maruts, the Ādityas)."""
    tail = group_key.rsplit(":", 1)[-1].replace("-", " ").lower()
    return {
        "group_key": group_key,
        "display_label": tail,
        "display_type": LABEL_DEITY_GROUP,
        "domain_model_version": DOMAIN_MODEL_VERSION,
    }
