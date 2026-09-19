"""Recitation audio: lookup by passage, by work, by id, and local cache streaming.

**Every route answers from the catalog, never from the graph.** The catalog is a sidecar
keyed by ``canonical_key`` precisely so that adding audio mutates neither the graph nor the
frozen ontology. The one thing these routes ask the graph is whether a key exists and what
its citation is, through the same :meth:`PassageService.resolve` every other passage route
uses -- so a client holding ``RV 1.1.1`` can call this endpoint without converting it
first, and a key that is not in the corpus 404s here exactly as it does elsewhere.

**The passage route's normal answer is a container's recording.** Nothing located for this
corpus has per-mantra timing, so asking about a verse returns its hymn's recitation with
``covers_requested_passage=false`` and a ``scope_note`` that says which hymn. That is not a
degraded answer; it is the accurate one, and it is returned as ``PARTIAL`` rather than
``SUPPORTED`` so a client cannot mistake it for a verse-level recording.

**The streaming route cannot be turned into an open proxy.** It takes an ``audio_id`` and
resolves it inside the catalog; there is no parameter that accepts a URL. Only records that
actually hold a local copy are streamable, the resolved path is confined under the cache
directory, and a remote record returns 409 with the direct URL the client should use
instead. Section 19 of the release spec forbids ``?url=<anything>`` and the shape of these
signatures is what enforces it.

**Route order is load-bearing.** ``/audio/stats`` is declared before ``/audio/{audio_id}``
and the ``/stream`` route before the bare detail route, because ``audio_id`` uses the
``path`` converter to admit the colons in ids like ``VEDSEARCH:RV:1.1.1``. A greedy
converter declared first would swallow both.
"""

from __future__ import annotations

import mimetypes
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.responses import FileResponse, StreamingResponse

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import (
    COMMON_ERROR_RESPONSES,
    AudioNotStreamableError,
    AudioUpstreamError,
    NotFoundError,
)
from vedagraph.api.models.audio import (
    AudioStatsResponse,
    AudioTrackView,
    PassageAudioResponse,
    WorkAudioResponse,
)
from vedagraph.api.models.common import CaveatView, KnowledgeStatus
from vedagraph.api.services.audio_service import AudioServiceDep
from vedagraph.api.services.passage_service import PassageService
from vedagraph.product.audio.models import Availability, PlaybackMode

router = APIRouter(tags=["Audio"], responses=COMMON_ERROR_RESPONSES)

KeyPath = Annotated[
    str,
    PathParam(
        description="A canonical key, a citation (RV 1.1.1) or a canonical URN.",
        examples=["VG:RV:SAK:M01:S001:V001", "RV 1.1.1", "VG:YV:VSM:A01"],
    ),
]

AudioIdPath = Annotated[
    str,
    PathParam(
        description="A catalog audio id.",
        examples=["VEDSEARCH:RV:1.1.1", "VEDSEARCH:YV:40.1.17"],
    ),
]

#: Bytes per chunk when serving a ranged read from the local cache. Large enough that a
#: full track is not thousands of syscalls, small enough that a seek is answered promptly.
_CHUNK: Final = 64 * 1024

_RANGE_RE: Final = re.compile(r"^bytes=(\d*)-(\d*)$")

#: Attached wherever a track is returned for a passage it does not individually cover.
_CONTAINER_SCOPE_CAVEAT: Final = CaveatView(
    text=(
        "This recording covers a whole structural span, not this verse alone. It is "
        "offered at the level its publisher recorded it, and the scope block states that "
        "level; playback begins at the start of the span rather than at this verse. Do not "
        "present it as a recording of one mantra."
    ),
    source="measured",
)

#: Attached when a recording is catalogued for this passage but the publisher answered a
#: definite 404. Distinct from "nothing is mapped": the mapping is right and the file is
#: gone, which is a different thing to tell a reader and a different thing to fix.
#:
#: This is not hypothetical, and it is not the same thing as the eleven Valakhilya hymns
#: (RV 8.49-8.59), which the source does not publish at all and which therefore produce no
#: record to be BROKEN in the first place.
_WITHDRAWN_AUDIO_CAVEAT: Final = CaveatView(
    text=(
        "A recitation is catalogued for this passage, but its publisher no longer serves "
        "the file. No player is offered rather than one that cannot play. This is a gap in "
        "the source, not a statement about the text."
    ),
    source="measured",
)

#: Attached when nothing is mapped. The wording matters: this API's whole discipline is
#: that an absence must say whose absence it is, and an unmapped recitation is ours.
_NO_AUDIO_CAVEAT: Final = CaveatView(
    text=(
        "No recording is mapped to this passage. That is a statement about this product's "
        "audio coverage and not about the tradition: recitation of this text certainly "
        "exists. Absence of audio here is never evidence of absence of a recitation."
    ),
    source="measured",
)


@router.get(
    "/passages/{key}/audio",
    summary="Recitation audio for one passage",
    description=(
        "Recordings covering this passage, nearest structural level first.\n\n"
        "The normal answer for a mantra is its **hymn's** recitation, with "
        "`scope.covers_requested_passage=false` and a ready-made `scope.scope_note`. "
        "Render `scope_note` verbatim and the label cannot overstate what the audio is.\n\n"
        "`data_status` is `NOT_BUILT` when nothing is mapped. That is a supported state, "
        "not an error, and the client should render no player at all rather than a "
        "disabled one."
    ),
    response_model=PassageAudioResponse,
)
def passage_audio(
    key: KeyPath,
    repository: RepositoryDep,
    service: AudioServiceDep,
    request: Request,
) -> PassageAudioResponse:
    passages = PassageService(repository)
    canonical_key = passages.resolve(key)
    summary = passages.summary(canonical_key)
    matches = service.catalog.resolve(canonical_key)
    # A record the publisher answered 404 for is dropped here rather than rendered. The
    # alternative is a play control that cannot play, which reads to a user as a defect in
    # the corpus. Only BROKEN is filtered: it is set solely on a definite 404 or 410, while
    # TEMPORARILY_UNAVAILABLE means one check did not land and the file may well play now.
    playable = [m for m in matches if m.record.availability is not Availability.BROKEN]

    if not playable:
        return PassageAudioResponse(
            passage_key=canonical_key,
            citation=summary.canonical_citation,
            tracks=[],
            data_status=KnowledgeStatus.NOT_BUILT,
            caveats=[_WITHDRAWN_AUDIO_CAVEAT if matches else _NO_AUDIO_CAVEAT],
        )
    matches = playable

    citations = service.citations_for(repository, [m.matched_key for m in matches])
    tracks = [
        service.track_view(
            match.record,
            request=request,
            levels_above=match.levels_above,
            matched_key=match.matched_key,
            matched_citation=citations.get(match.matched_key),
        )
        for match in matches
    ]
    own_level = all(match.is_own_level for match in matches)
    return PassageAudioResponse(
        passage_key=canonical_key,
        citation=summary.canonical_citation,
        tracks=tracks,
        # PARTIAL, not SUPPORTED: a container recording is a real answer about a wider
        # span than was asked for, which is exactly what PARTIAL means in this API.
        data_status=KnowledgeStatus.SUPPORTED if own_level else KnowledgeStatus.PARTIAL,
        caveats=[] if own_level else [_CONTAINER_SCOPE_CAVEAT],
    )


@router.get(
    "/works/{work_id}/audio",
    summary="Every recording for one Samhita",
    description=(
        "All catalogued recordings for the Veda this work addresses, with coverage counted "
        "live from the catalog.\n\n"
        "`mapped_scope_count` is distinct canonical keys with a recording -- not tracks and "
        "not mantras. For the Rigveda it is a count of suktas; a client that rendered it as "
        "a share of mantras would overstate coverage by an order of magnitude."
    ),
    response_model=WorkAudioResponse,
)
def work_audio(
    work_id: Annotated[str, PathParam(examples=["VG:WORK:RV:SAK", "VG:WORK:SV:KAU"])],
    repository: RepositoryDep,
    service: AudioServiceDep,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkAudioResponse:
    return service.work_audio(repository, work_id, request=request, limit=limit, offset=offset)


@router.get(
    "/audio/stats",
    summary="Catalog-wide audio figures",
    description=(
        "Every figure derived from the catalog on this request, so nothing here can drift "
        "from what the catalog says. A client rendering audio coverage must read these "
        "counts rather than hard-coding one, because the catalogue grows.\n\n"
        "`by_publication_tier` and `by_veda_and_tier` split the catalogue into "
        "`RELEASED_VERIFIED` -- a named person played it -- and "
        "`SOURCE_MAPPED_UNREVIEWED` -- mapped and checked by instrument, heard by nobody. "
        "The two sum to `total_records`. A surface that adds them and calls the total "
        "verified is the one thing this split exists to prevent.\n\n"
        "`by_availability` is reported beside the coverage counts on purpose: a catalog "
        "whose records were last measured unreachable is a different product state from one "
        "whose records answer, and omitting it would read as full coverage."
    ),
    response_model=AudioStatsResponse,
)
def audio_stats(service: AudioServiceDep) -> AudioStatsResponse:
    return service.stats()


@router.get(
    "/audio/{audio_id:path}/stream",
    summary="Stream a locally cached recording",
    description=(
        "Serves bytes for a catalog record that holds a local copy, with correct HTTP Range "
        "support so seeking works.\n\n"
        "Only catalog ids are accepted. There is no parameter that takes a URL, so this "
        "endpoint cannot be used as an open proxy, and a record whose audio is remote "
        "returns 409 naming the publisher's URL to use instead."
    ),
    response_class=FileResponse,
)
def stream_audio(
    audio_id: AudioIdPath,
    service: AudioServiceDep,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    record = service.catalog.by_id(audio_id)
    if record is None:
        raise NotFoundError(
            f"No catalogued recording has id {audio_id!r}.",
            hint="Call a passage's /audio route or GET /api/v1/audio/stats for valid ids.",
        )
    path = service.cached_path(record)
    if path is not None:
        return _ranged_file_response(path, range_header)

    if record.playback_mode is PlaybackMode.PROXIED_STREAM:
        # The source serves this verse as base64 inside JSON. Fetch, decode, and hand the
        # client real audio with working Range support. Only a catalogued id reaches here;
        # there is no parameter by which a caller could name a URL of their own.
        try:
            payload, content_type = service.proxied_bytes(record)
        except Exception as error:
            raise AudioUpstreamError(
                "The recitation could not be retrieved from its source.",
                hint=f"The source is {record.source_name}. The text on this page is "
                f"unaffected; try again shortly.",
            ) from error
        return _ranged_bytes_response(payload, content_type, range_header)

    raise AudioNotStreamableError(
        f"{audio_id!r} is catalogued but no local copy is held, so there are no bytes to stream.",
        hint=(
            f"Play it from the publisher at {record.media_url}"
            if record.media_url
            else f"Open the source page at {record.source_page}"
        ),
    )


@router.get(
    "/audio/{audio_id:path}",
    summary="One catalogued recording",
    description=(
        "One record with its full provenance: where it came from, what it claims to be, "
        "what this product mapped it to, and how certain that mapping is."
    ),
    response_model=AudioTrackView,
)
def audio_detail(
    audio_id: AudioIdPath,
    service: AudioServiceDep,
    request: Request,
) -> AudioTrackView:
    record = service.catalog.by_id(audio_id)
    if record is None:
        raise NotFoundError(
            f"No catalogued recording has id {audio_id!r}.",
            hint="Call GET /api/v1/audio/stats for the catalog's shape.",
        )
    return service.track_view(
        record,
        request=request,
        levels_above=0,
        matched_key=record.scope_key,
        matched_citation=None,
    )


def _unsatisfiable(size: int) -> Response:
    return Response(
        status_code=416,
        headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"},
    )


def _parse_range(range_header: str, size: int) -> tuple[int, int] | None:
    """``(start, end)`` inclusive, or ``None`` when the range cannot be satisfied."""
    match = _RANGE_RE.match(range_header.strip())
    if match is None:
        return None
    raw_start, raw_end = match.group(1), match.group(2)
    if raw_start == "" and raw_end == "":
        return None
    if raw_start == "":
        # A suffix range: "the last N bytes", clamped to the file.
        length = min(int(raw_end), size)
        start, end = size - length, size - 1
    else:
        start = int(raw_start)
        end = int(raw_end) if raw_end else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        return None
    return start, end


def _ranged_bytes_response(payload: bytes, content_type: str, range_header: str | None) -> Response:
    """Serve an in-memory payload, honouring a byte range.

    Separate from the file path because a proxied verse is already fully in memory -- it
    arrived as one base64 document -- so slicing beats re-opening a stream.
    """
    size = len(payload)
    if not range_header:
        return Response(
            content=payload,
            media_type=content_type,
            headers={"Accept-Ranges": "bytes"},
        )
    span = _parse_range(range_header, size)
    if span is None:
        return _unsatisfiable(size)
    start, end = span
    return Response(
        content=payload[start : end + 1],
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
        },
    )


def _ranged_file_response(path: Path, range_header: str | None) -> Response:
    """Serve a file, honouring a single byte range.

    Written out rather than delegated to :class:`FileResponse` for the ranged case because
    a player that cannot seek is the defect this endpoint exists to avoid, and Starlette's
    file response does not answer ``Range`` on its own. A malformed or unsatisfiable range
    gets 416 with a ``Content-Range`` naming the real size, which is what a player needs in
    order to retry correctly.
    """
    size = path.stat().st_size
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not range_header:
        return FileResponse(path, media_type=media_type, headers={"Accept-Ranges": "bytes"})

    span = _parse_range(range_header, size)
    if span is None:
        return _unsatisfiable(size)
    start, end = span

    def stream() -> Iterator[bytes]:
        remaining = end - start + 1
        with path.open("rb") as handle:
            handle.seek(start)
            while remaining > 0:
                chunk = handle.read(min(_CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        stream(),
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
        },
    )
