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


def avs_mantra_identity(kanda: int, sukta: int, mantra: int) -> tuple[str, str, UUID]:
    _positive(kanda, sukta, mantra)
    key = f"VG:AV:SAU:K{kanda:02d}:S{sukta:03d}:V{mantra:03d}"
    urn = f"urn:vedagraph:mantra:atharvaveda:shaunaka:kanda:{kanda}:sukta:{sukta}:mantra:{mantra}"
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
