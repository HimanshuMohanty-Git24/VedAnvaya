"""Entity identity, normalization, aliases, and the refusal to merge on similarity."""

from pathlib import Path

import pytest

from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID, entity_identity, rv_mantra_identity
from vedagraph.knowledge.normalize import (
    ascii_key,
    composite_parts,
    distinct_key,
    is_composite_label,
    normalize_label,
)
from vedagraph.knowledge.registry import (
    AliasRegistryEntry,
    EntityRegistryEntry,
    EntityResolver,
    load_aliases,
    load_entity_registry,
    load_resolvers,
)
from vedagraph.models.enums import (
    AliasType,
    DevataSubtype,
    KnowledgeEntityType,
    ResolutionStatus,
)
from vedagraph.models.knowledge import (
    RESOLVING_STATUSES,
    KnowledgeAssertion,
    KnowledgeEntity,
)

REGISTRY = Path("data/registry")


def _entry(key: str, label: str) -> EntityRegistryEntry:
    return EntityRegistryEntry(
        entity_key=key, entity_type=KnowledgeEntityType.DEVATA, preferred_label=label
    )


def test_normalization_folds_writing_only() -> None:
    assert normalize_label(" Gāyatrī	 Virāṭ ") == "gāyatrī virāṭ"
    assert normalize_label("iḻā-sarasvatī-mahī") == "iḻā-sarasvatī-mahī"
    # Soma and Pavamāna Soma are a semantic distinction the source keeps; so do we.
    assert normalize_label("pavamānaḥ somaḥ") != normalize_label("somaḥ")


def test_ascii_key_is_readable_and_distinct_key_keeps_length() -> None:
    assert ascii_key("gāyatrī") == "GAYATRI"
    assert ascii_key("dvipadā virāṭ") == "DVIPADA-VIRAT"
    assert distinct_key("aśvaḥ") == "ASHVAH"
    assert distinct_key("aśvāḥ") == "ASHVAAH"


def test_a_hyphen_marks_a_composite_but_a_dual_ending_does_not() -> None:
    assert is_composite_label("iḻā-sarasvatī-mahī")
    assert composite_parts("iḻā-sarasvatī-mahī") == ["iḻā", "sarasvatī", "mahī"]
    # Recognising mitrāvaruṇau as a dual needs morphology, which is interpretation.
    assert not is_composite_label("mitrāvaruṇau")


def test_entity_uuids_are_stable_and_do_not_touch_the_passage_namespace() -> None:
    key, urn, entity_id = entity_identity("DEVATA", "AGNIH")
    assert key == "VG:DEVATA:AGNIH"
    assert urn == "urn:vedagraph:entity:devata:agnih"
    assert entity_identity("DEVATA", "AGNIH") == (key, urn, entity_id)
    _, mantra_urn, mantra_id = rv_mantra_identity(1, 1, 1)
    assert mantra_urn.startswith("urn:vedagraph:mantra:")
    assert entity_id != mantra_id
    assert str(VEDAGRAPH_NAMESPACE_UUID) == "7c8cde94-2bc0-50e2-8819-568ae65a3ec4"


def test_the_resolver_never_merges_two_labels_that_only_look_alike() -> None:
    resolver = EntityResolver(
        KnowledgeEntityType.DEVATA,
        [_entry("VG:DEVATA:ASHVAH", "aśvaḥ"), _entry("VG:DEVATA:ASHVAAH", "aśvāḥ")],
        [],
    )
    assert resolver.resolve("aśvaḥ").entity_key == "VG:DEVATA:ASHVAH"
    assert resolver.resolve("aśvāḥ").entity_key == "VG:DEVATA:ASHVAAH"
    # A near miss is unresolved with candidates, not silently attached to a neighbour.
    unknown = resolver.resolve("asvah")
    assert unknown.entity_key is None
    assert unknown.status is ResolutionStatus.NEEDS_REVIEW
    assert resolver.candidates("asvah") == ["VG:DEVATA:ASHVAAH", "VG:DEVATA:ASHVAH"]


def test_resolution_ladder_statuses() -> None:
    alias = AliasRegistryEntry(
        entity_type=KnowledgeEntityType.DEVATA,
        alias="agnih",
        canonical="agniḥ",
        alias_type=AliasType.SOURCE_SPELLING,
        evidence="fixture",
    )
    resolver = EntityResolver(
        KnowledgeEntityType.DEVATA,
        [_entry("VG:DEVATA:AGNIH", "agniḥ"), _entry("VG:DEVATA:A-B", "a-b")],
        [alias],
    )
    assert resolver.resolve("agniḥ").status is ResolutionStatus.EXACT
    assert resolver.resolve("  AGNIḤ ").status is ResolutionStatus.NORMALIZED_EXACT
    assert resolver.resolve("agnih").status is ResolutionStatus.KNOWN_ALIAS
    assert resolver.resolve("a-b").status is ResolutionStatus.COMPOSITE_PRESERVED
    assert resolver.resolve("nothing").status is ResolutionStatus.NEEDS_REVIEW


def test_only_four_statuses_may_attach_a_canonical_entity() -> None:
    assert RESOLVING_STATUSES == {
        ResolutionStatus.EXACT,
        ResolutionStatus.NORMALIZED_EXACT,
        ResolutionStatus.KNOWN_ALIAS,
        ResolutionStatus.COMPOSITE_PRESERVED,
    }


def test_the_assertion_model_rejects_a_non_deterministic_resolution() -> None:
    _, _, entity_id = entity_identity("DEVATA", "AGNIH")
    _, _, subject_id = rv_mantra_identity(1, 1, 1)
    with pytest.raises(ValueError, match="may not attach a canonical entity"):
        KnowledgeAssertion(
            assertion_id=entity_id,
            subject_key="VG:RV:SAK:M01:S001:V001",
            subject_id=subject_id,
            predicate="HAS_DEVATA",
            object_key="VG:DEVATA:AGNIH",
            object_id=entity_id,
            source_label="agniḥ",
            source_assertion_id=entity_id,
            provenance_class="SOURCE_EXPLICIT",
            scope_origin="SUKTA_WIDE",
            resolution_method=ResolutionStatus.NEEDS_REVIEW,
            source_id="WSC2023",
            source_artifact_id="WSC2023.RV.ANUKRAMANI.M01",
            citation="RV 1.1.1",
        )


def test_a_duplicate_registry_key_or_label_is_refused() -> None:
    with pytest.raises(ValueError, match="duplicate preferred_label"):
        EntityResolver(
            KnowledgeEntityType.DEVATA,
            [_entry("VG:DEVATA:A", "agniḥ"), _entry("VG:DEVATA:B", "agniḥ")],
            [],
        )
    with pytest.raises(ValueError, match="duplicate entity_key"):
        EntityResolver(
            KnowledgeEntityType.DEVATA,
            [_entry("VG:DEVATA:A", "agniḥ"), _entry("VG:DEVATA:A", "indraḥ")],
            [],
        )


def test_an_alias_may_not_shadow_a_preferred_label() -> None:
    alias = AliasRegistryEntry(
        entity_type=KnowledgeEntityType.DEVATA,
        alias="agniḥ",
        canonical="indraḥ",
        alias_type=AliasType.SOURCE_SPELLING,
        evidence="fixture",
    )
    with pytest.raises(ValueError, match="also a preferred label"):
        EntityResolver(KnowledgeEntityType.DEVATA, [_entry("VG:DEVATA:A", "agniḥ")], [alias])


def test_the_committed_registries_load_and_carry_typed_evidenced_aliases() -> None:
    resolvers = load_resolvers(REGISTRY)
    assert set(resolvers) == set(KnowledgeEntityType)
    for alias in load_aliases(REGISTRY):
        assert alias.alias_type in AliasType
        assert len(alias.evidence) > 30
        # Nothing is called an epithet without evidence that it is one.
        assert alias.alias_type is not AliasType.EPITHET

    chandas = resolvers[KnowledgeEntityType.CHANDAS]
    assert chandas.resolve("gāyatrī").entity_key == "VG:CHANDAS:GAYATRI"
    assert chandas.resolve("jagatiī").status is ResolutionStatus.KNOWN_ALIAS
    assert chandas.resolve("jagatiī").entity_key == "VG:CHANDAS:JAGATI"


def test_devata_subtypes_default_to_unknown() -> None:
    entries = load_entity_registry(KnowledgeEntityType.DEVATA, root=REGISTRY)
    classified = [
        entry
        for entry in entries
        if entry.devata_subtype is not None and entry.devata_subtype is not DevataSubtype.UNKNOWN
    ]
    assert 0 < len(classified) < 10
    assert all(entry.devata_subtype is not None for entry in entries)
    assert {entry.entity_key for entry in classified} >= {
        "VG:DEVATA:MITRAVARUNAU",
        "VG:DEVATA:VISVEDEVAH",
    }


def test_a_subtype_on_a_non_devata_entity_is_refused() -> None:
    key, urn, entity_id = entity_identity("CHANDAS", "GAYATRI")
    with pytest.raises(ValueError, match="applies only to DEVATA"):
        KnowledgeEntity(
            entity_id=entity_id,
            entity_key=key,
            canonical_urn=urn,
            entity_type=KnowledgeEntityType.CHANDAS,
            preferred_label="gāyatrī",
            preferred_label_iast="gāyatrī",
            devata_subtype=DevataSubtype.PAIR,
            resolution_status=ResolutionStatus.EXACT,
        )
