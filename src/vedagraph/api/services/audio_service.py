"""Turning catalog records into audio responses, and resolving the local cache safely.

**Two responsibilities that both concern honesty about scope.** The first is composing
:class:`AudioTrackView` so that the scope block always states the level that answered --
see :func:`_scope_note`, which is the single place the reader-facing sentence is written,
so there is no second code path that could phrase a hymn recording as a verse's.

The second is resolving ``local_cache_path`` to a real file. That is a path-traversal
surface, and the catalog is a committed file a contributor edits by hand, so the resolution
is confined: the record's relative path is joined under the cache root, resolved, and
checked to still be inside it. A record naming ``../../.env`` produces ``None`` rather than
a file handle, and :class:`~vedagraph.product.audio.models.AudioRecord` additionally
refuses to load such a path at all. Two independent checks because this one is worth two.

**The catalog is loaded once per process.** It is a read-only JSONL file of tens of
thousands of lines -- a figure that has trebled twice during this build, which is why it is
not written down here -- and parsing it per request would be the most expensive thing in an
audio response. It is held on
``app.state`` beside the Neo4j repository, for the same reason and with the same lifetime.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Sequence
from pathlib import Path
from threading import Lock
from typing import Annotated, Final

from fastapi import Depends, Request

from vedagraph.api.errors import WorkNotFoundError
from vedagraph.api.models.audio import (
    AudioPlaybackView,
    AudioScopeView,
    AudioSourceView,
    AudioStatsResponse,
    AudioTrackView,
    WorkAudioResponse,
)
from vedagraph.api.models.common import CaveatView, KnowledgeStatus
from vedagraph.product.audio.catalog import (
    CACHE_RELATIVE_PATH,
    CATALOG_RELATIVE_PATH,
    AudioCatalog,
    scope_label,
    scope_plural,
    tier_note,
)
from vedagraph.product.audio.models import (
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)
from vedagraph.product.audio.net import USER_AGENT
from vedagraph.product.audio.vedsearch import VedSearchClient

#: Citation lookup for the keys a page of tracks names. One query for the whole page
#: rather than one per track: a work page can carry fifty tracks and fifty round trips to
#: render fifty labels is the shape that makes a page feel slow.
_CITATIONS_FOR_KEYS: Final = (
    "MATCH (p:Passage) WHERE p.canonical_key IN $keys "
    "RETURN p.canonical_key AS key, p.canonical_citation AS citation"
)


def _scope_note(record: AudioRecord, levels_above: int, matched_citation: str | None) -> str:
    """The one sentence a client may render verbatim. Written in exactly one place.

    The wording is chosen so that no reading of it implies a narrower span than the
    recording covers. A hymn's recitation reached from a verse reads "Recitation of this
    hymn (RV 1.1), which contains this verse" -- the recording, the span, and the
    relationship, in that order.
    """
    where = f" ({matched_citation})" if matched_citation else ""
    span = scope_label(record.scope_type)
    if record.mapping_confidence is MappingConfidence.EXTERNAL_ONLY:
        return (
            f"An external recording of {span}. Its position inside the corpus is not "
            f"established, so it is offered as a reference and not as any passage's "
            f"recitation."
        )
    if levels_above == 0:
        return f"Recitation of {span}{where}."
    return (
        f"Recitation of {span}{where}, which contains this passage. "
        f"No per-verse timing is published for it, so it plays from the start of {span}."
    )


#: Decoded audio held in memory, most-recently-used last.
#:
#: A seek in the player issues a fresh ranged request, and the upstream source serves audio
#: as base64 inside JSON -- so without this, dragging the scrubber would re-fetch and
#: re-decode the whole verse on every drag event. Bounded by count rather than bytes because
#: these files are uniform: the median measured verse is 65 KB, so 96 entries is roughly
#: 6 MB.
_PROXY_CACHE_ENTRIES: Final = 96

_proxy_cache: OrderedDict[str, tuple[bytes, str]] = OrderedDict()
_proxy_lock = Lock()


def _cache_get(audio_id: str) -> tuple[bytes, str] | None:
    with _proxy_lock:
        entry = _proxy_cache.get(audio_id)
        if entry is not None:
            _proxy_cache.move_to_end(audio_id)
        return entry


def _cache_put(audio_id: str, payload: tuple[bytes, str]) -> None:
    with _proxy_lock:
        _proxy_cache[audio_id] = payload
        _proxy_cache.move_to_end(audio_id)
        while len(_proxy_cache) > _PROXY_CACHE_ENTRIES:
            _proxy_cache.popitem(last=False)


class AudioService:
    """Read-only composition over the catalog."""

    def __init__(self, catalog: AudioCatalog, cache_root: Path) -> None:
        self._catalog = catalog
        self._cache_root = cache_root

    @property
    def catalog(self) -> AudioCatalog:
        return self._catalog

    def cached_path(self, record: AudioRecord) -> Path | None:
        """The real file behind a ``LOCAL_CACHE`` record, or ``None``.

        ``None`` for a record with no local copy, for a record whose file is missing, and
        for a record whose path escapes the cache root. The caller cannot tell those apart
        and does not need to: in all three cases there are no bytes this API may serve.
        """
        if not record.local_cache_path:
            return None
        candidate = (self._cache_root / record.local_cache_path).resolve()
        root = self._cache_root.resolve()
        if root not in candidate.parents and candidate != root:
            return None
        return candidate if candidate.is_file() else None

    def proxied_bytes(self, record: AudioRecord) -> tuple[bytes, str]:
        """Fetch, decode and return real audio bytes for a PROXIED_STREAM record.

        The upstream document is JSON carrying base64, which no browser can play, so this
        is the only path by which such a record becomes audible. Raises
        :class:`ValueError` when the source returns nothing decodable, which the route
        turns into a 502 rather than an empty 200 -- a zero-byte body would leave the
        player silently stuck.
        """
        cached = _cache_get(record.audio_id)
        if cached is not None:
            return cached
        client = VedSearchClient(user_agent=USER_AGENT)
        payload = client.audio_bytes(record.veda, record.source_reference or "")
        _cache_put(record.audio_id, payload)
        return payload

    def citations_for(self, repository: object, keys: Sequence[str]) -> dict[str, str]:
        """Canonical citations for a page of scope keys, in one query."""
        wanted = [key for key in dict.fromkeys(keys) if key]
        if not wanted:
            return {}
        run = getattr(repository, "run", None)
        if run is None:  # pragma: no cover - repository always has run
            return {}
        rows = run(_CITATIONS_FOR_KEYS, keys=wanted)
        return {
            str(row["key"]): str(row["citation"])
            for row in rows
            if row.get("key") and row.get("citation")
        }

    def track_view(
        self,
        record: AudioRecord,
        *,
        request: Request,
        levels_above: int,
        matched_key: str | None,
        matched_citation: str | None,
    ) -> AudioTrackView:
        return AudioTrackView(
            audio_id=record.audio_id,
            title=record.title,
            audio_type=record.audio_type,
            scope=AudioScopeView(
                scope_type=record.scope_type,
                scope_key=matched_key,
                scope_citation=matched_citation,
                covers_requested_passage=levels_above == 0
                and record.mapping_confidence is not MappingConfidence.EXTERNAL_ONLY,
                levels_above=levels_above,
                scope_note=_scope_note(record, levels_above, matched_citation),
            ),
            performer=record.performer,
            tradition=record.tradition,
            location=record.location,
            duration_seconds=record.duration_seconds,
            start_seconds=record.start_seconds,
            end_seconds=record.end_seconds,
            availability=record.availability,
            publication_tier=record.publication_tier,
            review_note=tier_note(record.publication_tier),
            mapping_confidence=record.mapping_confidence,
            mapping_method=record.mapping_method,
            text_verified=record.text_verified,
            source=AudioSourceView(
                name=record.source_name,
                page=record.source_page,
                licence=record.licence,
                attribution=record.attribution,
                open_in_new_window=True,
            ),
            playback=self._playback_view(record, request=request),
            notes=record.notes,
        )

    def _playback_view(self, record: AudioRecord, *, request: Request) -> AudioPlaybackView:
        """Resolve the mode to concrete URLs, demoting a cache miss rather than 404ing later.

        A record whose ``playback_mode`` is ``LOCAL_CACHE`` but whose file is absent is
        rewritten here to stream from the publisher if it can, and to a plain link if it
        cannot. Without that, a cache cleared between catalog write and request would give
        the client a ``stream_url`` that 409s -- a broken player rather than a working
        remote one.
        """
        cached = self.cached_path(record)
        if record.playback_mode is PlaybackMode.PROXIED_STREAM and cached is None:
            # media_url is deliberately withheld: it returns JSON, and a client that put it
            # in an <audio> element would play nothing and report a decode error.
            return AudioPlaybackView(
                mode=PlaybackMode.PROXIED_STREAM,
                stream_url=str(request.url_for("stream_audio", audio_id=record.audio_id)),
                media_url=None,
                embed_url=None,
                supports_seek=True,
                media_kind=_media_kind(record),
            )
        if record.playback_mode is PlaybackMode.LOCAL_CACHE and cached is not None:
            stream_url = str(request.url_for("stream_audio", audio_id=record.audio_id))
            return AudioPlaybackView(
                mode=PlaybackMode.LOCAL_CACHE,
                stream_url=stream_url,
                media_url=record.media_url,
                embed_url=record.embed_url,
                supports_seek=True,
                media_kind=_media_kind(record),
            )
        if record.media_url:
            return AudioPlaybackView(
                mode=PlaybackMode.REMOTE_DIRECT,
                stream_url=None,
                media_url=record.media_url,
                embed_url=record.embed_url,
                # Ranged requests were confirmed to work against this source, which is
                # what makes scrubbing function on a remote file.
                supports_seek=True,
                media_kind=_media_kind(record),
            )
        if record.embed_url:
            return AudioPlaybackView(
                mode=PlaybackMode.EXTERNAL_EMBED,
                embed_url=record.embed_url,
                supports_seek=False,
                media_kind=_media_kind(record),
            )
        return AudioPlaybackView(
            mode=PlaybackMode.EXTERNAL_LINK,
            supports_seek=False,
            media_kind=None,
        )

    def work_audio(
        self,
        repository: object,
        work_id: str,
        *,
        request: Request,
        limit: int,
        offset: int,
    ) -> WorkAudioResponse:
        veda = next((v for v, r in VEDA_RECENSIONS.items() if work_id == f"VG:WORK:{v}:{r}"), None)
        if veda is None:
            raise WorkNotFoundError(
                f"No work has id {work_id!r}.",
                hint="The four works are VG:WORK:RV:SAK, VG:WORK:SV:KAU, "
                "VG:WORK:YV:VSM and VG:WORK:AV:SAU.",
            )
        records = sorted(self._catalog.for_veda(veda), key=lambda r: r.audio_id)
        page = records[offset : offset + max(1, limit)]
        citations = self.citations_for(
            repository, [r.scope_key for r in page if r.scope_key is not None]
        )
        tracks = [
            self.track_view(
                record,
                request=request,
                levels_above=0,
                matched_key=record.scope_key,
                matched_citation=citations.get(record.scope_key or ""),
            )
            for record in page
        ]
        scope_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        for record in records:
            scope_counts[record.scope_type.value] = scope_counts.get(record.scope_type.value, 0) + 1
            name = record.source_name or "Unnamed source"
            source_counts[name] = source_counts.get(name, 0) + 1

        caveats = list(_work_caveats(veda, records))
        return WorkAudioResponse(
            work_id=work_id,
            veda=veda,
            recension=VEDA_RECENSIONS[veda],
            tracks=tracks,
            mapped_scope_count=len(self._catalog.scope_keys_for_veda(veda)),
            playable_scope_count=len(
                {
                    record.scope_key
                    for record in records
                    if record.scope_key is not None
                    and record.availability is not Availability.BROKEN
                }
            ),
            scope_type_counts=dict(sorted(scope_counts.items())),
            source_counts=dict(sorted(source_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            data_status=(KnowledgeStatus.NOT_BUILT if not records else KnowledgeStatus.PARTIAL),
            caveats=caveats,
        )

    def _stats_caveats(self) -> Iterable[CaveatView]:
        """Say what the counts mean, reading it off the catalog rather than asserting it.

        An earlier version of this method wrote the units into prose -- "a Rigvedic figure
        counts suktas and a Yajurvedic one counts adhyayas" -- which was true of the
        source in use at the time and became false when the catalog moved to one recording
        per verse. Worse, it then told a reader *not* to read the counts as a share of
        verses with their own recording, which is exactly what they had become. Derived
        text cannot drift that way.
        """
        catalog = self._catalog
        if not len(catalog):
            return

        scopes = {record.scope_type for record in catalog}
        if scopes == {AudioScope.MANTRA}:
            yield CaveatView(
                text=(
                    "Every count here is a count of verses, each with its own recording. "
                    "They are not a share of the corpus: a Veda's verses without a "
                    "recording are simply absent from these totals, and "
                    "`mapped_scope_keys_by_veda` beside each figure is what to compare "
                    "against that Veda's verse count."
                ),
                source="measured",
            )
        else:
            named = ", ".join(sorted(scope_plural(scope) for scope in scopes))
            yield CaveatView(
                text=(
                    f"These counts mix recording levels -- {named} -- so a single figure "
                    f"is not a count of verses. A recording of a wider span plays from the "
                    f"start of that span, not from the verse a reader is reading."
                ),
                source="measured",
            )

        # The tier split, stated in the payload's own prose and counted rather than typed.
        # An earlier policy made this unnecessary: nothing was published until it had been
        # heard, so the catalogue had one footing and needed no sentence about it. Under
        # the 2026-09-19 two-tier policy the catalogue has two, and a stats block that
        # reported only a total would read as though the whole of it had been reviewed.
        unreviewed = len(catalog.for_tier(PublicationTier.SOURCE_MAPPED_UNREVIEWED))
        verified = len(catalog.for_tier(PublicationTier.RELEASED_VERIFIED))
        if unreviewed:
            yield CaveatView(
                text=(
                    f"{unreviewed:,} of these {len(catalog):,} recordings have not been "
                    f"listened to by anyone. They are published because their mapping was "
                    f"checked against the source's coordinates and this corpus's text and "
                    f"their media resolves -- not because they were verified by ear. "
                    f"{verified:,} carry an audible review. Do not describe the total as "
                    f"human-verified."
                ),
                source="measured",
            )

        samavedic = catalog.for_veda("SV")
        if not samavedic:
            yield CaveatView(
                text=(
                    "No Samavedic recording is catalogued at all. The Samaveda is the one "
                    "Veda defined by its sung realisation, so this is the most "
                    "conspicuous gap in the layer -- and it is a gap in what has been "
                    "published, not a statement about the tradition."
                ),
                source="measured",
            )
        elif any(record.audio_type is AudioType.SAMAGANA for record in samavedic):
            yield CaveatView(
                text=(
                    "Some Samavedic entries are samagana -- the sung realisation -- which "
                    "this corpus's arcika text does not contain. Their presence is not "
                    "evidence that the gana corpus is held here."
                ),
                source="measured",
            )

    def stats(self) -> AudioStatsResponse:
        catalog = self._catalog
        cached = sum(1 for record in catalog if self.cached_path(record) is not None)
        caveats = list(self._stats_caveats())
        return AudioStatsResponse(
            total_records=len(catalog),
            by_veda=catalog.counts_by("veda"),
            by_publication_tier={
                tier.value: len(catalog.for_tier(tier)) for tier in PublicationTier
            },
            by_veda_and_tier=catalog.counts_by_veda_and_tier(),
            by_scope_type=catalog.counts_by("scope_type"),
            by_audio_type=catalog.counts_by("audio_type"),
            by_mapping_confidence=catalog.counts_by("mapping_confidence"),
            by_availability=catalog.counts_by("availability"),
            by_playback_mode=catalog.counts_by("playback_mode"),
            mapped_scope_keys_by_veda={
                veda: len(catalog.scope_keys_for_veda(veda)) for veda in sorted(VEDA_RECENSIONS)
            },
            locally_cached=cached,
            data_status=KnowledgeStatus.SUPPORTED if len(catalog) else KnowledgeStatus.NOT_BUILT,
            caveats=caveats,
        )


def _media_kind(record: AudioRecord) -> str | None:
    """'audio' or 'video', read off the media URL's extension.

    Two of the three portal series are MP4. A client that rendered every record in an
    ``<audio>`` element would play them with no picture and, worse, would report an error
    on some browsers -- so the kind travels with the payload.
    """
    if record.playback_mode is PlaybackMode.PROXIED_STREAM:
        # The upstream URL has no media extension -- it is a JSON endpoint -- but the
        # decoded payload is MP3, verified by sampling real files during discovery.
        return "audio"
    url = record.media_url or record.local_cache_path
    if not url:
        return None
    tail = url.rsplit(".", 1)[-1].lower()
    if tail in {"mp4", "webm", "mov", "m4v"}:
        return "video"
    if tail in {"mp3", "ogg", "oga", "wav", "m4a", "flac", "opus"}:
        return "audio"
    return None


def _work_caveats(veda: str, records: Sequence[AudioRecord]) -> Iterable[CaveatView]:
    if not records:
        if veda == "SV":
            # Worth saying plainly rather than leaving as a generic zero. The Samaveda is
            # the one Veda defined by its sung realisation, so its silence here is the most
            # conspicuous gap in the layer -- and it is a gap in what has been published
            # anywhere, not a gap this product chose.
            yield CaveatView(
                text=(
                    "No per-verse recitation is catalogued for the Samaveda. The source "
                    "that supplies the other three Vedas publishes Samavedic verse text "
                    "but no Sanskrit audio for it, and no other source located offers "
                    "Kauthuma arcika audio mapped to individual verses. This is an absence "
                    "in what exists publicly, not a statement about the tradition -- and it "
                    "is the Veda for which recitation matters most."
                ),
                source="measured",
            )
            return
        yield CaveatView(
            text=(
                "No recording is catalogued for this work. That is this product's audio "
                "coverage and not a statement about the tradition."
            ),
            source="measured",
        )
        return
    scopes = {record.scope_type for record in records}
    if scopes and scopes != {AudioScope.MANTRA}:
        named = ", ".join(sorted(scope_plural(s) for s in scopes))
        yield CaveatView(
            text=(
                f"These recordings cover whole {named} and not individual verses. "
                f"Each one plays from the start of its span."
            ),
            source="measured",
        )
    if veda == "SV":
        yield CaveatView(
            text=(
                "The Samavedic entries are collection-level and name no verse. This "
                "corpus's Samavedic text is the Kauthuma arcika and holds no gana, so a "
                "samagana recording renders a dimension the text layer does not contain."
            ),
            source="measured",
        )


def get_catalog(request: Request) -> AudioCatalog:
    """The process-wide catalog, loaded on first use and held on ``app.state``.

    Lazy rather than built in the lifespan so that a malformed catalog fails the first
    audio request with a readable error instead of preventing the whole product -- graph
    browsing, search, Ask -- from starting. Audio is the least load-bearing layer here and
    must not be able to take the rest down.
    """
    catalog = getattr(request.app.state, "audio_catalog", None)
    if catalog is None:
        data_dir = Path(getattr(request.app.state, "data_dir", "data"))
        catalog = AudioCatalog.load(data_dir / CATALOG_RELATIVE_PATH)
        request.app.state.audio_catalog = catalog
    assert isinstance(catalog, AudioCatalog)
    return catalog


def get_audio_service(request: Request) -> AudioService:
    data_dir = Path(getattr(request.app.state, "data_dir", "data"))
    return AudioService(get_catalog(request), data_dir / CACHE_RELATIVE_PATH)


AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]
