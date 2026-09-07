"""Stable canonical keys, URNs, and deterministic UUIDv5 identifiers."""

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


# Samaveda Kauthuma structural levels above the verse, outermost first. The
# selected GRETIL artifact declares this reference system in its own body:
#   arcika | prapathaka | ardha | dasati | verse | line
# ``line`` is a sub-verse pada label and is deliberately NOT an identity level.
SV_CONTAINER_LEVELS: tuple[str, ...] = ("arcika", "prapathaka", "ardha", "dasati")


def sv_mantra_identity(
    arcika: int, prapathaka: int, ardha: int, dasati: int, verse: int
) -> tuple[str, str, UUID]:
    """CANDIDATE identity for one Samaveda Kauthuma verse. NOT FROZEN.

    ``data/registry/works.yaml`` deliberately keeps ``key_pattern: null`` and
    ``identity_status: RESEARCH_REQUIRED`` for this work. The single artifact that
    evidences this structure was adjudicated unusable on both rights and edition-identity
    grounds, and every known digital Kauthuma text descends from the same encumbered
    lineage, so there is no independent witness against which to confirm a key. This
    function exists so pilots are coherent and so freezing later is a purely additive
    change. Nothing may treat its output as canonical Samaveda identity.

    Samaveda is the one work whose hierarchy depth is NOT uniform. The selected
    edition encodes an absent level as a literal ``0``: the Aranya arcika has no
    prapathaka and no ardha, and the Mahanamnya arcika additionally has no dasati.
    ``0`` is therefore a legitimate value here and :func:`_positive` must not be
    applied to it -- doing so would reject 65 real verses. ``arcika`` and ``verse``
    are still required to be positive.

    The 4th slot is deliberately not given a fixed cardinality: in the Purvarcika it
    is a true decad numbered 1-10 across the ardha, while in the Uttararcika it
    resets inside each ardha and holds only two or three verses. Same slot, different
    unit; the count is never assumed.

    The edition's own running verse number (1..1875) is defective -- five values
    absent, one duplicated -- and is recorded as a non-canonical ``Citation``, never
    as identity. See docs/FOUR_VEDA_STRUCTURAL_MODEL.md.
    """
    _positive(arcika, verse)
    _non_negative(prapathaka, ardha, dasati)
    key = f"VG:SV:KAU:A{arcika}:P{prapathaka:02d}:R{ardha}:D{dasati:02d}:V{verse:02d}"
    urn = (
        f"urn:vedagraph:mantra:samaveda:kauthuma:arcika:{arcika}"
        f":prapathaka:{prapathaka}:ardha:{ardha}:dasati:{dasati}:verse:{verse}"
    )
    return key, urn, uuid_for_urn(urn)


def sv_container_identity(
    arcika: int,
    prapathaka: int | None = None,
    ardha: int | None = None,
    dasati: int | None = None,
) -> tuple[str, str, UUID]:
    """CANDIDATE identity for one Samaveda container at variable depth. NOT FROZEN.

    Carries the same caveat as :func:`sv_mantra_identity`: the Samaveda key is not
    declared in the work registry and this output is not canonical.

    ``None`` means "this level is not part of this container's address" and truncates
    the key; ``0`` means "the source encodes this level as absent in this arcika" and
    is retained in the key so the address stays positionally parseable. The two are
    different facts and are not conflated.
    """
    _positive(arcika)
    supplied = [arcika, prapathaka, ardha, dasati]
    depth = 1
    for index in range(1, 4):
        if supplied[index] is None:
            if any(value is not None for value in supplied[index + 1 :]):
                raise ValueError(
                    "Samaveda container levels must be supplied outermost-first "
                    "without gaps; use 0 for a level the source marks absent"
                )
            break
        depth = index + 1
    _non_negative(*[value for value in supplied[1:depth] if value is not None])
    key_parts = ["VG:SV:KAU", f"A{arcika}"]
    urn_parts = ["urn:vedagraph:section:samaveda:kauthuma", f"arcika:{arcika}"]
    formats = ((1, "P{:02d}"), (2, "R{}"), (3, "D{:02d}"))
    for index, template in formats:
        if index >= depth:
            break
        value = supplied[index]
        key_parts.append(template.format(value))
        urn_parts.append(f"{SV_CONTAINER_LEVELS[index]}:{value}")
    key = ":".join(key_parts)
    urn = ":".join(urn_parts)
    return key, urn, uuid_for_urn(urn)


def _positive(*values: int) -> None:
    if any(value < 1 for value in values):
        raise ValueError("hierarchy values must be positive integers")


def _non_negative(*values: int) -> None:
    """Allow ``0`` for a hierarchy level the selected edition marks as absent.

    Only works whose declared reference system encodes absence as ``0`` may use this;
    Rigveda, Vajasaneyi and Atharvaveda all keep :func:`_positive`.
    """
    if any(value < 0 for value in values):
        raise ValueError("hierarchy values must not be negative")


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
