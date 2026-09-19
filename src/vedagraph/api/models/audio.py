"""Audio responses, shaped so a client cannot render a recording as more precise than it is.

**The field that does the work is** :attr:`AudioScopeView.covers_requested_passage`.
A recording does not always cover exactly the passage asked about. The present source
publishes one file per verse and the field is usually true -- but the first source tried
recorded whole suktas, so a client asking about a mantra got a hymn back, and had the
payload said only "here is a track", the obvious button beside a verse would have read
*Play this mantra* and been false 10,552 times in the Rigveda alone.

So the scope block states the level that answered, how many levels above the request it
sits, and a ready-made :attr:`AudioScopeView.scope_note` in prose. A client that renders
``scope_note`` verbatim cannot produce the misleading label, and a client that ignores all
three has to work at it.

**No field here is a rights assertion.** ``licence`` and ``attribution`` are carried
because a share-alike file requires its own attribution and because a reader deserves to
know where a recording came from, not as a redistribution clearance. Playback mode is what
governs what the product does with the bytes.

**Nothing exposes a filesystem path.** A locally cached record is played through
``stream_url``, which addresses a catalog id on this API. ``local_cache_path`` from the
catalog model is deliberately absent from every model in this module.
"""

from __future__ import annotations

from pydantic import Field

from vedagraph.api.models.common import ApiModel, CaveatView, KnowledgeStatus
from vedagraph.product.audio.models import (
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)


class AudioSourceView(ApiModel):
    """Where the recording came from, and what it is called there."""

    name: str = Field(description="The publishing body or archive.")
    page: str = Field(description="A page a reader can open to see the source's own labelling.")
    licence: str | None = Field(
        default=None,
        description="The per-file licence where the source states one. Never a collection "
        "default: a set that is partly CC BY-SA and partly CC0 would be misstated by one.",
    )
    attribution: str | None = None
    open_in_new_window: bool = Field(
        default=True,
        description="Always true. Several sources' terms prohibit being loaded into a "
        "frame, so the product never embeds a source page in one.",
    )


class AudioPlaybackView(ApiModel):
    """How the client should sound this record, and what it may not assume.

    Exactly one of the URL fields is populated for a playable mode. A client that finds
    them all null is looking at an :attr:`PlaybackMode.EXTERNAL_LINK` record and must
    offer the source page rather than a player.
    """

    mode: PlaybackMode
    stream_url: str | None = Field(
        default=None,
        description="This API's own streaming route, for records held in the local cache. "
        "Addresses a catalog id; no filesystem path is ever exposed and no arbitrary URL "
        "is ever proxied.",
    )
    media_url: str | None = Field(
        default=None, description="The publisher's direct media URL, streamed as-is."
    )
    embed_url: str | None = None
    supports_seek: bool = Field(
        default=False,
        description="Whether ranged requests are known to work, which is what makes "
        "scrubbing function. False means unverified, not broken.",
    )
    media_kind: str | None = Field(
        default=None,
        description="'audio' or 'video'. Carried because a source may serve either -- the "
        "first one tried served MP4 for two of its three Vedas -- and a client that assumed "
        "audio would fail silently on those.",
    )


class AudioScopeView(ApiModel):
    """What span the recording covers, relative to what the client asked about.

    The whole point of this block is that ``covers_requested_passage=false`` is the normal
    answer and must be rendered, not treated as an error.
    """

    scope_type: AudioScope
    scope_key: str | None = Field(
        default=None, description="The canonical key the recording is attached to."
    )
    scope_citation: str | None = Field(
        default=None, description="Human citation of that key, e.g. 'RV 1.1'."
    )
    covers_requested_passage: bool = Field(
        description="True only when the recording is of exactly the passage requested. "
        "False means it covers a container and the label must say so."
    )
    levels_above: int = Field(
        ge=0,
        description="How far above the requested passage the recording sits. 0 is the "
        "passage itself; 1 is its immediate container.",
    )
    scope_note: str = Field(
        description="Reader-facing prose for this scope, safe to render verbatim. For a "
        "verse's own recording this reads 'Recitation of this verse (RV 1.1.1).'; for a "
        "hymn recording reached from a verse it reads 'Recitation of this hymn (RV 1.1), "
        "which contains this passage' -- never 'play this mantra'."
    )


class AudioTrackView(ApiModel):
    """One recording, everything a reader needs to judge it, and nothing more."""

    audio_id: str
    title: str
    audio_type: AudioType = Field(
        description="SAMAGANA marks a Samavedic melodic performance, which is NOT the "
        "arcika text this corpus holds."
    )
    scope: AudioScopeView
    performer: str | None = Field(
        default=None,
        description="Null where the source names none. The current source names no reciter "
        "anywhere reached, so these are null and the UI says 'not stated by the source' "
        "rather than inventing a tradition.",
    )
    tradition: str | None = None
    location: str | None = None
    duration_seconds: float | None = Field(
        default=None, description="Measured where measured; null is unmeasured, not zero."
    )
    start_seconds: float | None = None
    end_seconds: float | None = None
    availability: Availability
    publication_tier: PublicationTier = Field(
        default=PublicationTier.SOURCE_MAPPED_UNREVIEWED,
        description="Whether a person has heard this recording. "
        "`SOURCE_MAPPED_UNREVIEWED` is the normal answer and must never be rendered with "
        "the words 'verified', 'human verified' or 'audibly verified'. Render "
        "`review_note` verbatim and the label cannot overstate it.",
    )
    review_note: str = Field(
        description="Reader-facing prose for `publication_tier`, safe to render verbatim. "
        "Written in one place so no second code path can phrase an unheard recording as a "
        "checked one."
    )
    mapping_confidence: MappingConfidence
    mapping_method: str = Field(
        description="How this recording came to be attached to this passage, in one "
        "reproducible phrase. Carried in the payload so provenance does not depend on "
        "the reader finding a document."
    )
    text_verified: bool = Field(
        default=False,
        description="Whether the text the source says this recording recites was compared "
        "against this corpus's own text for the passage, and matched. Exposed because the "
        "difference between a checked mapping and a plausible one is exactly what a reader "
        "cannot hear until it is wrong.",
    )
    source: AudioSourceView
    playback: AudioPlaybackView
    notes: str | None = None


class PassageAudioResponse(ApiModel):
    """The answer to "is there a recording for this passage?".

    ``data_status`` is :attr:`KnowledgeStatus.NOT_BUILT` when the catalog holds nothing for
    this passage, because that absence is about this product's coverage and not about the
    tradition. No audio is a supported state and never an error.
    """

    passage_key: str
    citation: str | None = None
    tracks: list[AudioTrackView] = Field(default_factory=list)
    data_status: KnowledgeStatus
    caveats: list[CaveatView] = Field(default_factory=list)


class WorkAudioResponse(ApiModel):
    """Every recording for one Samhita, with live coverage figures.

    Coverage is counted from the catalog on each request rather than stored, so a figure
    in the product cannot drift from the catalog the way a written-down number would.
    """

    work_id: str
    veda: str
    recension: str
    tracks: list[AudioTrackView] = Field(default_factory=list)
    mapped_scope_count: int = Field(
        description="Distinct canonical keys with a recording, for this Veda."
    )
    playable_scope_count: int = Field(
        description="Of those, the keys whose recording the publisher still serves.\n\n"
        "Reported separately because the two differ and the difference is user-visible: the "
        "portal maps all 1,028 Rigvedic suktas and serves 1,017 of them, having never "
        "published the eleven Valakhilya hymns. A surface that rendered only "
        "`mapped_scope_count` would promise a recitation for eleven passages that offer no "
        "player."
    )
    scope_type_counts: dict[str, int] = Field(default_factory=dict)
    source_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Recordings per publisher, over the whole Veda rather than over the page "
        "of `tracks` returned. "
        "Present because a surface that derived this from `tracks` would be describing a "
        "sample as though it were the population, and one did: the Rigveda's recitation "
        "panel read its publishers off the first page of tracks and named the Cologne "
        "collection, which supplies 150 of its 10,552 recordings, as the source of the "
        "collection.",
    )
    data_status: KnowledgeStatus
    caveats: list[CaveatView] = Field(default_factory=list)


class AudioStatsResponse(ApiModel):
    """Catalog-wide figures, all derived.

    Deliberately reports ``by_availability`` beside the coverage counts. A catalog whose
    records were mostly last measured as unreachable is a different product state from one
    where they answer, and a stats block that omitted it would read as full coverage.

    Reports ``by_publication_tier`` for the same reason. Since 2026-09-19 the catalogue
    holds recordings nobody has listened to, and a single total would let a surface call
    all of them verified.
    """

    total_records: int
    by_veda: dict[str, int] = Field(default_factory=dict)
    by_publication_tier: dict[str, int] = Field(
        default_factory=dict,
        description="Records per tier. Sums to `total_records`, which is the invariant a "
        "client may rely on: there is no third, hidden state.\n\n"
        "`RELEASED_VERIFIED` counts recordings a named person played. "
        "`SOURCE_MAPPED_UNREVIEWED` counts recordings mapped and checked by instrument and "
        "heard by nobody. A surface that adds them together and calls the total 'verified' "
        "is the one failure this split exists to make impossible.",
    )
    by_veda_and_tier: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="`{veda: {tier: count}}`, with every tier present for every Veda even "
        "at zero -- so a Veda with no reviewed recordings renders as '0 reviewed' rather "
        "than rendering as nothing. Read this rather than hard-coding a coverage figure.",
    )
    by_scope_type: dict[str, int] = Field(default_factory=dict)
    by_audio_type: dict[str, int] = Field(default_factory=dict)
    by_mapping_confidence: dict[str, int] = Field(default_factory=dict)
    by_availability: dict[str, int] = Field(default_factory=dict)
    by_playback_mode: dict[str, int] = Field(default_factory=dict)
    mapped_scope_keys_by_veda: dict[str, int] = Field(default_factory=dict)
    locally_cached: int = 0
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)
