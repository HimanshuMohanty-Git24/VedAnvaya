"""Stable canonical keys, URNs, and deterministic UUIDv5 identifiers."""

from enum import StrEnum
from uuid import UUID, uuid5

# Generated once from the VedaGraph namespace seed and now a permanent protocol constant.
# Changing this value would change every entity UUID.
VEDAGRAPH_NAMESPACE_UUID = UUID("7c8cde94-2bc0-50e2-8819-568ae65a3ec4")


def uuid_for_urn(canonical_urn: str) -> UUID:
    if not canonical_urn.startswith("urn:vedagraph:"):
        raise ValueError("canonical URNs must start with 'urn:vedagraph:'")
    return uuid5(VEDAGRAPH_NAMESPACE_UUID, canonical_urn)


def rv_mantra_key(mandala: int, sukta: int, mantra: int) -> str:
    _positive(mandala, sukta, mantra)
    return f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}:V{mantra:03d}"


def rv_sukta_key(mandala: int, sukta: int) -> str:
    _positive(mandala, sukta)
    return f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}"


def rv_mandala_key(mandala: int) -> str:
    _positive(mandala)
    return f"VG:RV:SAK:M{mandala:02d}"


def rv_mandala_identity(mandala: int) -> tuple[str, str, UUID]:
    _positive(mandala)
    key = rv_mandala_key(mandala)
    urn = f"urn:vedagraph:section:rigveda:shakala:mandala:{mandala}"
    return key, urn, uuid_for_urn(urn)


def rv_sukta_identity(mandala: int, sukta: int) -> tuple[str, str, UUID]:
    _positive(mandala, sukta)
    key = rv_sukta_key(mandala, sukta)
    urn = f"urn:vedagraph:hymn:rigveda:shakala:mandala:{mandala}:sukta:{sukta}"
    return key, urn, uuid_for_urn(urn)


def rv_mantra_urn(mandala: int, sukta: int, mantra: int) -> str:
    _positive(mandala, sukta, mantra)
    return f"urn:vedagraph:mantra:rigveda:shakala:mandala:{mandala}:sukta:{sukta}:mantra:{mantra}"


def rv_mantra_identity(mandala: int, sukta: int, mantra: int) -> tuple[str, str, UUID]:
    key = rv_mantra_key(mandala, sukta, mantra)
    urn = rv_mantra_urn(mandala, sukta, mantra)
    return key, urn, uuid_for_urn(urn)


def vsm_mantra_identity(adhyaya: int, mantra: int) -> tuple[str, str, UUID]:
    _positive(adhyaya, mantra)
    key = f"VG:YV:VSM:A{adhyaya:02d}:V{mantra:03d}"
    urn = f"urn:vedagraph:mantra:yajurveda:vajasaneyi-madhyandina:adhyaya:{adhyaya}:mantra:{mantra}"
    return key, urn, uuid_for_urn(urn)


def vsm_adhyaya_key(adhyaya: int) -> str:
    _positive(adhyaya)
    return f"VG:YV:VSM:A{adhyaya:02d}"


def vsm_adhyaya_identity(adhyaya: int) -> tuple[str, str, UUID]:
    """Identity for one Vajasaneyi Adhyaya, the work's only structural container."""
    key = vsm_adhyaya_key(adhyaya)
    urn = f"urn:vedagraph:section:yajurveda:vajasaneyi-madhyandina:adhyaya:{adhyaya}"
    return key, urn, uuid_for_urn(urn)


def avs_kanda_key(kanda: int) -> str:
    _positive(kanda)
    return f"VG:AV:SAU:K{kanda:02d}"


def avs_sukta_key(kanda: int, sukta: int) -> str:
    _positive(kanda, sukta)
    return f"VG:AV:SAU:K{kanda:02d}:S{sukta:03d}"


def avs_kanda_identity(kanda: int) -> tuple[str, str, UUID]:
    key = avs_kanda_key(kanda)
    urn = f"urn:vedagraph:section:atharvaveda:shaunaka:kanda:{kanda}"
    return key, urn, uuid_for_urn(urn)


def avs_sukta_identity(kanda: int, sukta: int) -> tuple[str, str, UUID]:
    key = avs_sukta_key(kanda, sukta)
    urn = f"urn:vedagraph:hymn:atharvaveda:shaunaka:kanda:{kanda}:sukta:{sukta}"
    return key, urn, uuid_for_urn(urn)


def avs_mantra_identity(kanda: int, sukta: int, mantra: int) -> tuple[str, str, UUID]:
    _positive(kanda, sukta, mantra)
    key = f"VG:AV:SAU:K{kanda:02d}:S{sukta:03d}:V{mantra:03d}"
    urn = f"urn:vedagraph:mantra:atharvaveda:shaunaka:kanda:{kanda}:sukta:{sukta}:mantra:{mantra}"
    return key, urn, uuid_for_urn(urn)


class SamavedaCollection(StrEnum):
    """The named verse collections of the Kauthuma samhita.

    Naming the collection instead of numbering it is what makes Samaveda identity
    referent-stable. The two witnesses disagree about the ARITY of the top level: the
    Pandey e-text lineage (GRETIL, TITUS) presents four flat sibling arcikas, while the
    selected Sanskrit Wikisource corpus, Griffith, the Vedic Heritage Portal and
    B. R. Sharma present two -- Purvarcika and Uttararcika -- with Chanda, Aranya and
    Mahanamnya as sections inside the Purvarcika. A bare ordinal therefore does not
    denote a stable collection: slot-1 value ``2`` means Aranyarcika in one lineage and
    Uttararcika in the other, which is a 1,225-verse referent collision.

    Both readings agree completely on WHICH collections exist and on what belongs to
    each. Keying on the collection's own name records exactly that agreement and leaves
    the arity question -- whether Chanda is a sibling of Uttara or a child of Purva --
    to the container hierarchy, where changing it renumbers nothing.
    """

    CHANDA = "CHANDA"
    ARANYA = "ARANYA"
    MAHANAMNYA = "MAHANAMNYA"
    UTTARA = "UTTARA"


# The levels each collection actually declares between itself and the verse, outermost
# first. These are not a uniform five-slot address: the selected witness gives the
# Chanda collection a prapathaka and a dasati but no ardha, gives the Aranya collection
# only a dasati, gives the Mahanamnya collection neither, and gives the Uttara collection
# all three. A level absent from a collection is OMITTED from the key rather than written
# as a literal ``0``; writing ``0`` was the previous scheme's way of recording a level
# that the rejected artifact invented, and it made an edition's flattening choice part of
# canonical identity.
SV_COLLECTION_LEVELS: dict[SamavedaCollection, tuple[str, ...]] = {
    SamavedaCollection.CHANDA: ("prapathaka", "dasati"),
    SamavedaCollection.ARANYA: ("dasati",),
    SamavedaCollection.MAHANAMNYA: (),
    SamavedaCollection.UTTARA: ("prapathaka", "ardha", "dasati"),
}

# Every level is padded to the same width, so a Samaveda key sorts lexicographically in
# coordinate order and no level can silently become mixed-width. The previous scheme left
# the arcika and ardha slots unpadded, which made ``A10`` sort before ``A2`` and made the
# verse slot two digits at ``V01`` and three at ``V100``. Measured over the selected
# witness, the widest value any level takes is the Uttararcika's 23 dasatis, so two digits
# is sufficient; SV_MAX_LEVEL_VALUE pins that so the width cannot drift.
_SV_LEVEL_KEY_FORMAT: dict[str, str] = {
    "prapathaka": "P{:02d}",
    "ardha": "R{:02d}",
    "dasati": "D{:02d}",
}

SV_MAX_LEVEL_VALUE = 99

# Kept for the container spine and for any caller that needs the full level vocabulary.
SV_CONTAINER_LEVELS: tuple[str, ...] = ("collection", "prapathaka", "ardha", "dasati")


def _sv_levels(
    collection: SamavedaCollection,
    *,
    prapathaka: int | None,
    ardha: int | None,
    dasati: int | None,
) -> list[tuple[str, int]]:
    """Validate the supplied levels against the collection's declared shape.

    A level the collection does not have is refused rather than coerced, and a level it
    does have is required. This is what stops a caller reintroducing the flattened
    five-slot address by passing ``ardha=0`` into a collection that has no ardha.

    ``0`` is refused as loudly as any other value, and that is the whole point. An earlier
    revision exempted it -- ``value not in (None, 0)`` -- which meant old five-slot code
    ported by mechanically passing zeros got SILENCE from this path while the container
    path refused the same input. Silence is the migration hazard: it produces a
    well-formed key from a caller that still believes in the flattened address.
    """
    supplied = {"prapathaka": prapathaka, "ardha": ardha, "dasati": dasati}
    declared = SV_COLLECTION_LEVELS[collection]
    for name, value in supplied.items():
        if name not in declared and value is not None:
            raise ValueError(
                f"the Samaveda {collection.value} collection declares no {name} level, "
                f"so {name}={value!r} cannot be part of a canonical address"
            )
    levels: list[tuple[str, int]] = []
    for name in declared:
        value = supplied[name]
        if value is None:
            raise ValueError(
                f"the Samaveda {collection.value} collection declares a {name} level, "
                "so it is required for a canonical address"
            )
        _positive(value)
        _within_key_width(name, value)
        levels.append((name, value))
    return levels


def _within_key_width(level: str, value: int) -> None:
    """Refuse a value too wide for the key's fixed-width slot.

    Failing closed here keeps every Samaveda key the same length, so lexicographic order
    equals coordinate order and no key can become a prefix of another.
    """
    if value > SV_MAX_LEVEL_VALUE:
        raise ValueError(
            f"Samaveda {level}={value} exceeds the fixed key width; widening the slot "
            "would renumber every existing key and requires an explicit migration"
        )


def sv_mantra_identity(
    collection: SamavedaCollection | str,
    *,
    verse: int,
    prapathaka: int | None = None,
    ardha: int | None = None,
    dasati: int | None = None,
) -> tuple[str, str, UUID]:
    """Identity for one Samaveda Kauthuma verse.

    Key shapes, one per collection, each exactly the levels the selected witness
    declares for that collection::

        VG:SV:KAU:CHANDA:P{prapathaka:02d}:D{dasati:02d}:V{verse:02d}
        VG:SV:KAU:ARANYA:D{dasati:02d}:V{verse:02d}
        VG:SV:KAU:MAHANAMNYA:V{verse:02d}
        VG:SV:KAU:UTTARA:P{prapathaka:02d}:R{ardha:02d}:D{dasati:02d}:V{verse:02d}

    ``verse`` is the DASATI-LOCAL index, never the samhita running number. The running
    number 1..1875 is recorded as a non-canonical ``Citation`` and never as identity: it
    is attested only by the hand-keyed wiki text and by the Pandey lineage, and the one
    located print witness carries a per-section counter instead. See Refusal 3 in
    docs/FOUR_VEDA_STRUCTURAL_MODEL.md.

    Nothing about this key depends on a TextVersion, a source URL or the source's own
    text. Passage identity stays source-independent; the binding between a key and the
    textual occurrence it denotes is asserted separately and guarded at release time by
    :class:`vedagraph.models.PassageReferentBinding`.
    """
    resolved = SamavedaCollection(collection)
    _positive(verse)
    _within_key_width("verse", verse)
    levels = _sv_levels(resolved, prapathaka=prapathaka, ardha=ardha, dasati=dasati)
    key_parts = ["VG:SV:KAU", resolved.value]
    urn_parts = ["urn:vedagraph:mantra:samaveda:kauthuma", resolved.value.lower()]
    for name, value in levels:
        key_parts.append(_SV_LEVEL_KEY_FORMAT[name].format(value))
        urn_parts.append(f"{name}:{value}")
    key = ":".join([*key_parts, f"V{verse:02d}"])
    urn = ":".join([*urn_parts, f"verse:{verse}"])
    return key, urn, uuid_for_urn(urn)


def sv_container_identity(
    collection: SamavedaCollection | str,
    *,
    prapathaka: int | None = None,
    ardha: int | None = None,
    dasati: int | None = None,
) -> tuple[str, str, UUID]:
    """Identity for one Samaveda container, truncated at the deepest level supplied.

    Levels must be supplied outermost-first without gaps, and only levels the collection
    declares may be supplied at all.
    """
    resolved = SamavedaCollection(collection)
    declared = SV_COLLECTION_LEVELS[resolved]
    supplied = {"prapathaka": prapathaka, "ardha": ardha, "dasati": dasati}
    for name, value in supplied.items():
        if name not in declared and value is not None:
            raise ValueError(f"the Samaveda {resolved.value} collection declares no {name} level")
    depth = 0
    for index, name in enumerate(declared):
        if supplied[name] is None:
            if any(supplied[later] is not None for later in declared[index + 1 :]):
                raise ValueError(
                    "Samaveda container levels must be supplied outermost-first without gaps"
                )
            break
        depth = index + 1
    key_parts = ["VG:SV:KAU", resolved.value]
    urn_parts = ["urn:vedagraph:section:samaveda:kauthuma", resolved.value.lower()]
    for name in declared[:depth]:
        value = supplied[name]
        assert value is not None
        _positive(value)
        _within_key_width(name, value)
        key_parts.append(_SV_LEVEL_KEY_FORMAT[name].format(value))
        urn_parts.append(f"{name}:{value}")
    key = ":".join(key_parts)
    urn = ":".join(urn_parts)
    return key, urn, uuid_for_urn(urn)


def _positive(*values: int) -> None:
    if any(value < 1 for value in values):
        raise ValueError("hierarchy values must be positive integers")


def entity_identity(entity_type: str, slug: str) -> tuple[str, str, UUID]:
    """Identity for a canonical knowledge-layer entity.

    Entity URNs live under ``urn:vedagraph:entity:`` and therefore cannot collide with
    passage URNs; the passage namespace and its UUIDs are untouched by this layer.
    """
    if not entity_type or not slug:
        raise ValueError("entity type and slug are required")
    key = f"VG:{entity_type}:{slug}"
    urn = f"urn:vedagraph:entity:{entity_type.lower()}:{slug.lower()}"
    return key, urn, uuid_for_urn(urn)
