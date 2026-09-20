"""The audio content layer: a catalog of recitations keyed by canonical passage identity.

Nothing in here writes to Neo4j. See :mod:`vedagraph.product.audio.models` for why the
catalog is a sidecar and :mod:`vedagraph.product.audio.catalog` for how a per-mantra
reader surface gets an honest answer out of per-sukta recordings.
"""

from vedagraph.product.audio.catalog import (
    CACHE_RELATIVE_PATH,
    CATALOG_RELATIVE_PATH,
    AudioCatalog,
    AudioMatch,
    ancestor_keys,
    scope_label,
    scope_plural,
    tier_label,
    tier_note,
    work_id_for_veda,
    write_catalog,
)
from vedagraph.product.audio.models import (
    SCOPE_TO_ENTITY_TYPES,
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)

__all__ = [
    "CACHE_RELATIVE_PATH",
    "CATALOG_RELATIVE_PATH",
    "SCOPE_TO_ENTITY_TYPES",
    "VEDA_RECENSIONS",
    "AudioCatalog",
    "AudioMatch",
    "AudioRecord",
    "AudioScope",
    "AudioType",
    "Availability",
    "MappingConfidence",
    "PlaybackMode",
    "PublicationTier",
    "ancestor_keys",
    "scope_label",
    "scope_plural",
    "tier_label",
    "tier_note",
    "work_id_for_veda",
    "write_catalog",
]
