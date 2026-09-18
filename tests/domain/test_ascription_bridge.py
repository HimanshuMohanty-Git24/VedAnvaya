"""The AV ascription -> canonical Devata bridge, and the six ways it must refuse.

GAP-CROSS-VEDA-DEVATA-IDENTITY-BRIDGE-001. Every test is paired BAD -> FAIL / GOOD -> PASS,
and four of them encode the owner's ``must_not_do`` list verbatim.
"""

from __future__ import annotations

import pytest

from vedagraph.domain import ascription_bridge as bridge

DEVATAS = [
    {
        "entity_key": "VG:DEVATA:AGNIH",
        "label_iast": "agni",
        "preferred_label": "agniḥ",
        "aliases_iast": ["agne"],
    },
    {
        "entity_key": "VG:DEVATA:INDRAH",
        "label_iast": "indra",
        "preferred_label": "indraḥ",
        "aliases_iast": [],
    },
    {
        "entity_key": "VG:DEVATA:SOMAH",
        "label_iast": "soma",
        "preferred_label": "somaḥ",
        "aliases_iast": [],
    },
    # Both spellings are taken verbatim from the live registry, including the fact that the
    # two nodes SHARE the aliases "pavamāna" and "pavamānaḥ". That shared alias is why the
    # ambiguity refusal is load-bearing here rather than decorative.
    {
        "entity_key": "VG:DEVATA:PAVAMANAH",
        "label_iast": "pavamāna",
        "preferred_label": "pavamānaḥ",
        "aliases_iast": ["pavamāna", "pavamānaḥ"],
    },
    {
        "entity_key": "VG:DEVATA:PAVAMANAH-SOMAH",
        "label_iast": "pavamāna soma",
        "preferred_label": "pavamānaḥ somaḥ",
        "aliases_iast": ["pavamāna", "pavamānaḥ"],
    },
    {
        "entity_key": "VG:DEVATA:ASVINAU",
        "label_iast": "aśvinau",
        "preferred_label": "aśvinau",
        "aliases_iast": [],
    },
    {
        "entity_key": "VG:DEVATA:BRHASPATIH",
        "label_iast": "bṛhaspati",
        "preferred_label": "bṛhaspatiḥ",
        "aliases_iast": [],
    },
]


def _asc(label: str, key: str = "VG:ASCRIPTION:AV:X", occ: int = 1) -> dict[str, object]:
    return {"entity_key": key, "label_iast": label, "occurrence_count": occ}


def _resolve(label: str) -> bridge.Resolution:
    index = bridge.SurfaceIndex.build(DEVATAS)
    return bridge.resolve_one(_asc(label), index)


def test_the_vrddhi_path_is_what_the_probe_did_not_have() -> None:
    """GOOD: the implicit taddhita resolves. It is the majority of the 324 labels."""
    assert _resolve("āindram").devata_key == "VG:DEVATA:INDRAH"
    assert _resolve("āgneyam").devata_key == "VG:DEVATA:AGNIH"
    assert _resolve("sāumyam").devata_key == "VG:DEVATA:SOMAH"
    assert _resolve("bārhaspatyam").devata_key == "VG:DEVATA:BRHASPATIH"
    assert _resolve("āçvinam").devata_key == "VG:DEVATA:ASVINAU"
    assert all(
        _resolve(label).derivation_path == "VRDDHI_TADDHITA"
        for label in ("āindram", "sāumyam", "bārhaspatyam")
    )


def test_vrddhi_falls_on_the_first_vowel_not_the_first_character() -> None:
    """BAD: an onset-blind de-vrddhi. It resolved 4 of 324 instead of 19.

    ``vāruṇam`` is ``v`` + vṛddhi of ``a``; a reversal anchored at index 0 never sees it.
    """
    assert ("varuṇam", "ā->a") in bridge.devrddhi("vāruṇam")
    assert ("bṛhaspatyam", "ār->ṛ") in bridge.devrddhi("bārhaspatyam")
    # A word with no vṛddhi in its first syllable yields no reversal at all.
    assert bridge.devrddhi("indram") == []
    # And the onset is preserved rather than eaten: the bug that produced 4 of 324 was a
    # reversal anchored at index 0, which never fires on a consonant-initial word.
    assert all(candidate.startswith("v") for candidate, _ in bridge.devrddhi("vāruṇam"))


def test_a_compound_naming_two_ascriptions_is_never_resolved_to_one() -> None:
    """must_not_do: resolving a compound of two ascriptions to a single deity."""
    result = _resolve("bārhaspatyam uta vāiçvadevam")
    assert result.status == "UNRESOLVED_COMPOUND_TWO_ASCRIPTIONS"
    assert result.devata_key is None
    assert result.reason
    # GOOD: the same head alone does resolve.
    assert _resolve("bārhaspatyam").devata_key == "VG:DEVATA:BRHASPATIH"


def test_a_plurality_is_never_resolved_to_a_single_deity() -> None:
    """must_not_do: resolving a plurality such as bahudevatyam."""
    for label in ("bahudevatyam", "nānādevatyam", "nānādāivatam"):
        result = _resolve(label)
        assert result.status == "UNRESOLVED_NAMES_A_PLURALITY", label
        assert result.devata_key is None


def test_a_subject_descriptor_is_not_a_deity() -> None:
    """must_not_do: resolving bhaisajyam, which is healing, to a deity at all."""
    for label in ("bhāiṣajyam", "āyuṣyam", "mantroktam"):
        result = _resolve(label)
        assert result.status == "UNRESOLVED_SUBJECT_DESCRIPTOR_NOT_A_DEITY", label
        assert result.devata_key is None


def test_the_anukramanis_own_deferral_marker_resolves_to_nothing() -> None:
    """lingokta is a null, not a god. A community containing it contains a null value."""
    result = _resolve("lin̄goktadevatyam")
    assert result.status == "UNRESOLVED_SOURCE_DEFERS_TO_THE_MANTRA"
    assert result.devata_key is None


def test_soma_and_pavamana_are_not_re_merged_by_the_looser_tier() -> None:
    """The settled owner decision, defended by the ambiguity refusal.

    BAD: ``pāvamānam`` folds, under vowel-length insensitivity, onto both
    ``VG:DEVATA:PAVAMANAH`` and ``VG:DEVATA:PAVAMANAH-SOMAH``. must_not_do says an
    ambiguous stem may not be resolved by picking the more frequent Devata, so it resolves
    to neither.
    """
    index = bridge.SurfaceIndex.build(DEVATAS)
    assert index.exact["pavamāna"] == {"VG:DEVATA:PAVAMANAH", "VG:DEVATA:PAVAMANAH-SOMAH"}
    assert bridge.length_collisions(DEVATAS)["pavamana"] == [
        "VG:DEVATA:PAVAMANAH",
        "VG:DEVATA:PAVAMANAH-SOMAH",
    ]

    result = _resolve("pāvamānam")
    assert result.status == "UNRESOLVED_AMBIGUOUS_TWO_OR_MORE_DEVATAS"
    assert result.devata_key is None
    assert set(result.candidates_matched) == {
        "VG:DEVATA:PAVAMANAH",
        "VG:DEVATA:PAVAMANAH-SOMAH",
    }
    assert bridge.check_resolutions([result])["soma_and_pavamana_not_merged"]

    # GOOD: soma itself is unambiguous and still resolves.
    assert _resolve("sāumyam").devata_key == "VG:DEVATA:SOMAH"


def test_the_fold_maps_transcription_systems_and_nothing_else() -> None:
    """Prove the fold. Over- and under-normalising both look like a clean run.

    Whitney's ``ç`` is the registry's ``ś`` -- a transcription equivalence with no
    ambiguity. ``ś`` is NOT folded to ``s``: the IAST acute is both a palatal sibilant and
    an udatta, and collapsing it is how a fold silently inverts an identity.
    """
    assert bridge.fold("āçvinam") == "āśvinam"
    assert bridge.fold("lin̄gokta") == "liṅgokta"
    assert bridge.fold("agniḥ") == "agni"
    assert bridge.fold("ŚRADDHĀ") == "śraddhā"
    assert "s" != bridge.fold("ś")
    assert bridge.fold("ś") == "ś", "the acute must survive the fold"
    # Vowel length survives the fold and is removed only by the explicit second tier.
    assert bridge.fold("pūṣan") == "pūṣan"
    assert bridge.shorten("pūṣan") == "puṣan"


def test_an_unresolvable_descriptor_still_carries_an_explicit_reason() -> None:
    """The closure test's own clause. BAD: a status outside the closed vocabulary."""
    unresolvable = _resolve("kṛtyāpratiharaṇam")
    assert unresolvable.status in bridge.RESOLUTION_STATUSES
    assert unresolvable.reason

    good = bridge.check_resolutions([unresolvable])
    assert good["passes"]

    bad = bridge.check_resolutions(
        [
            bridge.Resolution(
                ascription_key="VG:ASCRIPTION:AV:BAD",
                label="x",
                occurrences=0,
                status="MADE_UP_STATUS",
                reason="",
            )
        ]
    )
    assert not bad["every_status_in_vocabulary"]
    assert not bad["every_unresolved_has_a_reason"]
    assert not bad["passes"]


def test_a_resolution_without_a_derivation_path_is_a_display_label_join() -> None:
    """BAD: a resolution produced with no stated derivation. That is the forbidden join."""
    bad = bridge.check_resolutions(
        [
            bridge.Resolution(
                ascription_key="VG:ASCRIPTION:AV:BAD",
                label="agni",
                occurrences=1,
                status="RESOLVED_TO_CANONICAL_DEVATA",
                devata_key="VG:DEVATA:AGNIH",
                derivation_path=None,
                reason="matched the label",
            )
        ]
    )
    assert not bad["no_display_label_join"]
    assert not bad["passes"]

    good = bridge.check_resolutions([_resolve("āgneyam")])
    assert good["no_display_label_join"]
    assert good["passes"]


# ---------------------------------------------------------------------------
# The property contract: two axes, and neither slot is this module's to redefine
# ---------------------------------------------------------------------------


def test_the_emitted_vocabulary_is_the_products_own() -> None:
    """BAD -> FAIL: the three values this bridge shipped on its first pass.

    ``DERIVED_FROM_ANUKRAMANI_ASCRIPTION_MORPHOLOGY``,
    ``DERIVED_FROM_TADDHITA_MORPHOLOGY`` and ``SOURCE_EXPLICIT_ASCRIPTION_RESOLVED`` are all
    outside the closed enums, so ``EvidenceSurface`` and
    ``basis_from_attribution_precision`` both resolved to ``UNKNOWN`` for 921 live edges.
    The generator must refuse to emit them rather than let a guard find them after import.
    """
    with pytest.raises(bridge.UnmappedPropertyValue, match="EvidenceSurface"):
        bridge.check_property_vocabulary(
            [
                {
                    "evidence_basis": "DERIVED_FROM_ANUKRAMANI_ASCRIPTION_MORPHOLOGY",
                    "attribution_precision": "SOURCE_EXPLICIT_ASCRIPTION_RESOLVED",
                }
            ]
        )
    with pytest.raises(bridge.UnmappedPropertyValue):
        bridge.check_property_vocabulary(
            [{"evidence_basis": "SOURCE_METADATA", "attribution_precision": "MADE_UP"}]
        )

    good = bridge.check_property_vocabulary(
        [{"evidence_basis": "SOURCE_METADATA", "attribution_precision": "CONTAINER_INHERITED"}]
    )
    assert good["passes"]


def test_the_local_vocabularies_match_the_product_enums() -> None:
    """The literals here are a copy, so they must be asserted equal to the originals.

    Held as literals because importing the API package into the domain layer would invert
    the dependency. A copy nobody checks is how two spellings of one rule start.
    """
    from vedagraph.api.models.common import AttributionPrecision, EvidenceSurface

    assert bridge.PRODUCT_EVIDENCE_SURFACES == {member.value for member in EvidenceSurface}
    assert bridge.PRODUCT_ATTRIBUTION_PRECISIONS == {
        member.value for member in AttributionPrecision
    }


def test_an_exact_resolution_does_not_upgrade_a_container_wide_scope() -> None:
    """The two axes, kept apart. This is the question the lead asked.

    Measured: all 882 derived dedications come from ascription edges carrying
    ``CONTAINER_INHERITED`` / ``SUKTA_WIDE``; ``scope_container_key`` is the sukta on 882 of
    882 and the verse on 0; and all 505 ascribed Atharvavedic suktas carry the identical
    ascription set on every verse. The Anukramani states a deity for the HYMN. So the
    dedication is container-inherited even though the resolution step is exact, and the
    exactness lives on its own namespaced property instead of inflating the scope.
    """
    resolved = _resolve("āgneyam")
    props = bridge.dedication_properties(resolved, "VG:ASCRIPTION:AV:AGNEYAM-CA54")

    assert props["attribution_precision"] == "CONTAINER_INHERITED"
    assert props["scope_origin"] == "SUKTA_WIDE"
    assert props["evidence_basis"] == "SOURCE_METADATA"
    # The resolution axis survives, in its own namespace, and says the match was exact.
    assert props["ascription_resolution_comparison_tier"] == "EXACT"
    assert props["ascription_resolution_method"] == "TADDHITA_SASYA_DEVATA_DERIVATION"
    # ... and it is NOT allowed to leak into the scope slot.
    assert "EXACT" not in props["attribution_precision"]
    assert "SOURCE_EXPLICIT" not in props["attribution_precision"]
    bridge.check_property_vocabulary([props])


def test_the_bridge_edge_is_not_an_attribution() -> None:
    """(:DevataAscription)->(:Devata) joins a descriptor to its stem. It attributes nothing.

    The attribution lives on the passage edge, which is where a scope question belongs.
    """
    props = bridge.edge_properties(_resolve("āgneyam"))
    assert props["attribution_precision"] == "NOT_AN_ATTRIBUTION"
    assert props["evidence_basis"] == "SOURCE_METADATA"
    bridge.check_property_vocabulary([props])


def test_both_predicates_are_declared_with_endpoint_signatures() -> None:
    """An undeclared predicate is invisible to /api/v1/graph, which is safe and silent.

    ``RESOLVES_TO_DEVATA`` was invented for a relation ``ASCRIBES_TO_DEVATA`` already
    declares, with the right signature and a docstring describing this exact derivation. It
    sat at 0 edges because nothing was looking for it.
    """
    from vedagraph.domain import ontology

    assert ontology.REL_ASCRIBES_TO_DEVATA in ontology.DOMAIN_RELATIONSHIP_TYPES
    assert ontology.REL_HAS_DEVATA_DERIVED in ontology.DOMAIN_RELATIONSHIP_TYPES
    assert ontology.RELATIONSHIP_SIGNATURES[ontology.REL_ASCRIBES_TO_DEVATA] == (
        frozenset({ontology.LABEL_DEVATA_ASCRIPTION}),
        frozenset({ontology.LABEL_DEVATA}),
    )
    assert ontology.RELATIONSHIP_SIGNATURES[ontology.REL_HAS_DEVATA_DERIVED] == (
        frozenset({ontology.LABEL_PASSAGE, ontology.LABEL_MANTRA}),
        frozenset({ontology.LABEL_DEVATA}),
    )
    assert "RESOLVES_TO_DEVATA" not in ontology.DOMAIN_RELATIONSHIP_TYPES

    from vedagraph.api.services.graph_service import PREDICATE_SEMANTICS

    for predicate in ("ASCRIBES_TO_DEVATA", "HAS_DEVATA_DERIVED"):
        assert predicate in PREDICATE_SEMANTICS, predicate
        assert PREDICATE_SEMANTICS[predicate].limit


# ---------------------------------------------------------------------------
# GAP-ATTRIBUTION-002 clause 1 -- the vrddhi-spelled suffix
# ---------------------------------------------------------------------------


def test_the_vrddhi_spelled_suffix_generates_a_candidate_at_all() -> None:
    """BAD -> FAIL: no candidate, not a failed match.

    ``DEITY_ADJECTIVE_SUFFIXES`` spells the suffix with a short a and Whitney prints
    ``-dāivatam`` with a long one. Suffix stripping ran before any length folding, so these
    surfaces produced an EMPTY candidate list and the ``LENGTH_INSENSITIVE`` tier that
    ``resolve_one`` applies to the candidate *stem* never received a stem to apply itself
    to. 41 of the 210 stem-unresolved descriptors were in that state.

    The distinction matters for the diagnosis: a descriptor that generates a candidate and
    matches nothing is honestly unresolved, and one that generates no candidate has not been
    tried.
    """
    for label in ("agnidāivatam", "indradāivatam", "ātmadevatākam"):
        assert bridge.suffix_candidates(bridge.fold(label)), label


def test_the_two_named_vrddhi_descriptors_resolve_to_their_registered_deities() -> None:
    """GOOD -> PASS, on the two descriptors the diagnosis named."""
    agni = _resolve("agnidāivatam")
    assert agni.status == "RESOLVED_TO_CANONICAL_DEVATA"
    assert agni.devata_key == "VG:DEVATA:AGNIH"
    assert agni.stem == "agni"

    indra = _resolve("indradāivatam")
    assert indra.status == "RESOLVED_TO_CANONICAL_DEVATA"
    assert indra.devata_key == "VG:DEVATA:INDRAH"
    assert indra.stem == "indra"


def test_the_looser_suffix_tier_is_recorded_on_the_derivation_path() -> None:
    """A resolution that needed the looser suffix match says so.

    Folding the tier into the existing ``DEITY_ADJECTIVE_SUFFIX`` path would make the two
    indistinguishable in the graph, and then nobody could count how much of the layer rests
    on the looser comparison. ``agnidāivatam`` reaches the exact STEM tier because ``agni``
    is spelled with short vowels; it is the SUFFIX match that was loose, and the path is
    where that is recorded.
    """
    agni = _resolve("agnidāivatam")
    assert agni.derivation_path == "DEITY_ADJECTIVE_SUFFIX_LENGTH_FOLDED"
    assert agni.comparison_tier == "EXACT"

    atma = bridge.suffix_candidates(bridge.fold("ātmadāivatam"))
    assert atma and atma[0].path == "DEITY_ADJECTIVE_SUFFIX_LENGTH_FOLDED"

    # And an exactly-spelled suffix still takes the exact path, so the fix did not
    # relabel the 12 resolutions that never needed it.
    aditi = bridge.suffix_candidates(bridge.fold("aditidevatyam"))
    assert aditi and aditi[0].path == "DEITY_ADJECTIVE_SUFFIX"


def test_the_looseness_reaches_the_suffix_and_stops_there() -> None:
    """The stem keeps its own vowel lengths; only the suffix spelling is folded.

    This is the guard against the fix becoming the global loosening the owner decision
    bars. ``sūryadāivatam`` must yield the stem ``sūrya`` and not ``surya``: the stem is
    sliced out of the source fold, never out of the shortened probe. If the slice were
    taken from the probe, every long vowel in every stem would be destroyed and the
    resolver would start matching deities that differ only in vowel length.
    """
    candidates = bridge.suffix_candidates(bridge.fold("sūryadāivatam"))
    assert candidates
    assert candidates[0].stem == "sūrya"
    assert candidates[0].stem != "surya"


def test_a_descriptor_that_is_not_this_formation_still_does_not_resolve() -> None:
    """BAD -> FAIL: the false-positive controls.

    The looser suffix tier must not turn a non-deity surface into a deity. ``varuṇam`` has
    no deity-adjective suffix at all and must not be handed one; ``sūryadāivatam`` generates
    a candidate whose stem is not in this registry and must stay unresolved rather than fall
    to a near neighbour; and ``somadāivatam`` would resolve only if ``soma`` were reachable,
    which it is -- so the negative control is the one whose stem genuinely is absent.
    """
    # Generates a candidate, stem absent from the registry: honestly unresolved.
    surya = _resolve("sūryadāivatam")
    assert surya.status == "UNRESOLVED_STEM_MATCHES_NO_CANONICAL_DEVATA"
    assert surya.devata_key is None

    # A transcription-damaged tail must not be read as the suffix family.
    assert not bridge.suffix_candidates(bridge.fold("adtvatyam"))

    # And the ambiguity refusal still holds through the new tier: the shared pavamāna
    # alias must not be re-merged by a suffix that reaches two deities.
    ambiguous = _resolve("pavamānadāivatam")
    assert ambiguous.status == "UNRESOLVED_AMBIGUOUS_TWO_OR_MORE_DEVATAS"
    assert ambiguous.devata_key is None
    assert set(ambiguous.candidates_matched) == {
        "VG:DEVATA:PAVAMANAH",
        "VG:DEVATA:PAVAMANAH-SOMAH",
    }


def test_the_source_literal_survives_the_resolution() -> None:
    """Provenance: the stored label is Whitney's spelling, not the folded probe."""
    resolution = _resolve("agnidāivatam")
    assert resolution.label == "agnidāivatam"
    assert "ā" in resolution.label
    assert resolution.taddhita_suffix == "daivatam"
