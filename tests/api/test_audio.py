"""The audio routes' contract, and the three things a client must not be able to conclude.

The first is that a container's recording is a verse's recording. The catalog is now
per-verse, so the common case is honest by construction -- but the resolution logic still
supports container-scope records, and the copy that keeps them honest is still load-bearing.
Both shapes are exercised here, and the container tests assert on the exact prose in
``scope_note`` rather than only on the boolean beside it, because the boolean is what a
careful client reads and the prose is what a hurried one renders.

The second is that this API will fetch something arbitrary on a caller's behalf. The
streaming route takes a catalog id and nothing else; there is no parameter anywhere on the
audio surface that accepts a URL, and one test asserts that over the generated schema.

The third is that a third party's outage is this product's outage. A source that fails to
answer is a 502 naming audio, not the 503 that means the knowledge graph is down.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, build_client
from vedagraph.product.audio.catalog import AudioCatalog
from vedagraph.product.audio.models import (
    AudioRecord,
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
)

HYMN_KEY = "VG:RV:SAK:M01:S001"
VERSE_KEY = "VG:RV:SAK:M01:S001:V001"


def verse_record(**overrides: object) -> AudioRecord:
    """The shape discovery actually produces: one verse, verified, proxied."""
    base: dict[str, object] = {
        "audio_id": "VEDSEARCH:RV:1.1.1",
        "veda": "RV",
        "recension": "SAK",
        "scope_type": AudioScope.MANTRA,
        "scope_key": VERSE_KEY,
        "audio_type": AudioType.RECITATION,
        "title": "Rigveda RV 1.1.1 - recitation of this verse",
        "source_name": "VedSearch",
        "source_page": "https://vedsearch.org/rigved/1/1/1",
        "media_url": "https://vedsearch.org/api/v1/attachment/audio/rigved/1.1.1/sanskrit",
        "mapping_method": "mapped by coordinates and confirmed against the recited text",
        "mapping_confidence": MappingConfidence.EXACT,
        "availability": Availability.AVAILABLE,
        "playback_mode": PlaybackMode.PROXIED_STREAM,
        "source_reference": "1.1.1",
        "text_verified": True,
        "last_verified": "2026-09-12",
    }
    base.update(overrides)
    return AudioRecord(**base)  # type: ignore[arg-type]


def hymn_record(**overrides: object) -> AudioRecord:
    """A container-scope record, for the copy that must stay honest about wider spans."""
    base: dict[str, object] = {
        "audio_id": "LEGACY:RV:sukta-01-001",
        "veda": "RV",
        "recension": "SAK",
        "scope_type": AudioScope.SUKTA,
        "scope_key": HYMN_KEY,
        "audio_type": AudioType.RECITATION,
        "title": "Rigveda 1.1 - recitation of the whole sukta",
        "source_name": "An archive",
        "source_page": "https://example.invalid/rv/1/1",
        "media_url": "https://example.invalid/rv_01_001.mp3",
        "mapping_method": "derived from the publisher's own one-file-per-sukta path scheme",
        "mapping_confidence": MappingConfidence.STRUCTURAL,
        "availability": Availability.AVAILABLE,
        "playback_mode": PlaybackMode.REMOTE_DIRECT,
        "last_verified": "2026-09-12",
    }
    base.update(overrides)
    return AudioRecord(**base)  # type: ignore[arg-type]


#: Enough of the graph for the passage routes: a key resolves, and the node comes back.
def _script(key: str) -> dict[str, list[dict[str, object]]]:
    return {
        "RETURN p.canonical_key AS canonical_key": [{"canonical_key": key}],
        "RETURN p.canonical_key AS key, p.canonical_citation AS citation": [
            {"key": HYMN_KEY, "citation": "RV 1.1"},
            {"key": VERSE_KEY, "citation": "RV 1.1.1"},
        ],
        "AS passage": [
            {
                "passage": {
                    "canonical_key": key,
                    "canonical_citation": "RV 1.1.1",
                    "canonical_urn": "urn:vedagraph:mantra:rigveda:shakala:1:1:1",
                    "entity_id": "0" * 8,
                    "veda": "RV",
                    "work_id": "VG:WORK:RV:SAK",
                    "entity_type": "MANTRA",
                    "display_label": "RV 1.1.1",
                    "native_labels": "[]",
                    "hierarchy": '{"mandala":1,"sukta":1,"mantra":1}',
                    "parent_key": HYMN_KEY,
                    "sequence_in_parent": 1,
                }
            }
        ],
    }


def client_for(
    catalog: AudioCatalog, *, key: str = VERSE_KEY, data_dir: Path | None = None
) -> tuple[FastAPI, TestClient, FakeRepository]:
    repository = FakeRepository(_script(key))
    app, client = build_client(repository)
    app.state.audio_catalog = catalog
    if data_dir is not None:
        app.state.data_dir = data_dir
    return app, client, repository


@pytest.fixture
def verse_client() -> Iterator[TestClient]:
    app, client, repository = client_for(AudioCatalog([verse_record()]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([verse_record()])
        yield client


@pytest.fixture
def hymn_client() -> Iterator[TestClient]:
    app, client, repository = client_for(AudioCatalog([hymn_record()]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([hymn_record()])
        yield client


@pytest.fixture
def silent_client() -> Iterator[TestClient]:
    app, client, repository = client_for(AudioCatalog(()))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog(())
        yield client


# ---------------------------------------------------------------------------
# Per-verse audio: the answer the new source makes possible
# ---------------------------------------------------------------------------


def test_a_verse_gets_its_own_recording(verse_client: TestClient) -> None:
    payload = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    scope = payload["tracks"][0]["scope"]
    assert scope["covers_requested_passage"] is True
    assert scope["levels_above"] == 0
    assert scope["scope_type"] == "MANTRA"


def test_a_verse_level_answer_is_supported(verse_client: TestClient) -> None:
    """No caveat is needed when the recording really is of the passage asked for."""
    payload = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    assert payload["data_status"] == "SUPPORTED"
    assert payload["caveats"] == []


def test_the_verse_scope_note_names_the_verse(verse_client: TestClient) -> None:
    note = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]["scope"][
        "scope_note"
    ]
    assert "this verse" in note.lower()


def test_a_verse_record_is_exact_and_text_verified(verse_client: TestClient) -> None:
    track = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]
    assert track["mapping_confidence"] == "EXACT"
    assert "recited text" in track["mapping_method"]


def test_a_proxied_track_is_played_through_this_api(verse_client: TestClient) -> None:
    """The source serves JSON, so the client must be given our route and not that URL."""
    playback = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0][
        "playback"
    ]
    assert playback["mode"] == "PROXIED_STREAM"
    assert "/stream" in playback["stream_url"]
    assert playback["media_url"] is None
    assert playback["media_kind"] == "audio"
    assert playback["supports_seek"] is True


def test_no_response_field_leaks_the_upstream_json_endpoint(
    verse_client: TestClient,
) -> None:
    """A client that put that URL in an <audio> element would play nothing."""
    body = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").text
    assert "attachment/audio" not in body
    assert "local_cache_path" not in body


# ---------------------------------------------------------------------------
# Container scope: still supported, still honest
# ---------------------------------------------------------------------------


def test_a_container_recording_is_flagged_as_wider(hymn_client: TestClient) -> None:
    scope = hymn_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]["scope"]
    assert scope["covers_requested_passage"] is False
    assert scope["levels_above"] == 1
    assert scope["scope_key"] == HYMN_KEY


def test_a_container_answer_is_partial_and_carries_its_caveat(
    hymn_client: TestClient,
) -> None:
    payload = hymn_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    assert payload["data_status"] == "PARTIAL"
    assert payload["caveats"]


def test_the_container_scope_note_never_calls_a_hymn_a_verse(
    hymn_client: TestClient,
) -> None:
    """The Section 20 requirement, and the wording a hurried client renders verbatim."""
    note = (
        hymn_client.get(f"/api/v1/passages/{VERSE_KEY}/audio")
        .json()["tracks"][0]["scope"]["scope_note"]
        .lower()
    )
    assert "hymn" in note
    assert "this verse" not in note
    assert "mantra" not in note


# ---------------------------------------------------------------------------
# Absence
# ---------------------------------------------------------------------------


def test_an_unmapped_passage_is_not_built_and_carries_no_player(
    silent_client: TestClient,
) -> None:
    """No audio is a supported state. An empty track list must not read as an error."""
    response = silent_client.get(f"/api/v1/passages/{VERSE_KEY}/audio")
    assert response.status_code == 200
    payload = response.json()
    assert payload["tracks"] == []
    assert payload["data_status"] == "NOT_BUILT"
    assert payload["caveats"]


def test_the_absence_caveat_blames_the_product_not_the_tradition(
    silent_client: TestClient,
) -> None:
    text = (
        silent_client.get(f"/api/v1/passages/{VERSE_KEY}/audio")
        .json()["caveats"][0]["text"]
        .lower()
    )
    assert "coverage" in text
    assert "never evidence of absence" in text


def test_a_broken_recording_yields_no_player_and_says_why() -> None:
    """A record the source answered 404 for must not render a control that cannot play."""
    app, client, repository = client_for(
        AudioCatalog([verse_record(availability=Availability.BROKEN)])
    )
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([verse_record(availability=Availability.BROKEN)])
        payload = client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    assert payload["tracks"] == []
    assert payload["data_status"] == "NOT_BUILT"
    assert "no longer serves" in payload["caveats"][0]["text"]


def test_a_withdrawn_recording_reads_differently_from_an_unmapped_one() -> None:
    """Two absences that need different wording: our gap against the publisher's."""
    app_a, client_a, repo_a = client_for(
        AudioCatalog([verse_record(availability=Availability.BROKEN)])
    )
    with client_a:
        app_a.state.repository = repo_a
        app_a.state.audio_catalog = AudioCatalog([verse_record(availability=Availability.BROKEN)])
        withdrawn = client_a.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    app_b, client_b, repo_b = client_for(AudioCatalog(()))
    with client_b:
        app_b.state.repository = repo_b
        app_b.state.audio_catalog = AudioCatalog(())
        unmapped = client_b.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    assert withdrawn["caveats"][0]["text"] != unmapped["caveats"][0]["text"]


def test_a_temporarily_unavailable_recording_is_still_offered() -> None:
    """One failed check is not proof the file is gone."""
    record = verse_record(availability=Availability.TEMPORARILY_UNAVAILABLE)
    app, client, repository = client_for(AudioCatalog([record]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([record])
        payload = client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()
    assert len(payload["tracks"]) == 1


def test_an_unknown_passage_is_a_404_not_an_empty_answer() -> None:
    repository = FakeRepository({})
    app, client = build_client(repository)
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog(())
        assert client.get("/api/v1/passages/VG:RV:SAK:M99:S999/audio").status_code == 404


def test_a_graph_outage_is_a_503_that_names_no_host(down_client: TestClient) -> None:
    response = down_client.get(f"/api/v1/passages/{VERSE_KEY}/audio")
    assert response.status_code == 503
    assert "bolt" not in response.text.lower()
    assert "localhost" not in response.text.lower()


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_a_track_carries_its_source_and_mapping_method(verse_client: TestClient) -> None:
    track = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]
    assert track["source"]["name"]
    assert track["source"]["page"].startswith("https://")
    assert len(track["mapping_method"].split()) > 5


def test_an_unnamed_reciter_is_null_and_not_invented(verse_client: TestClient) -> None:
    track = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]
    assert track["performer"] is None


def test_source_pages_are_flagged_to_open_in_a_new_window(
    verse_client: TestClient,
) -> None:
    track = verse_client.get(f"/api/v1/passages/{VERSE_KEY}/audio").json()["tracks"][0]
    assert track["source"]["open_in_new_window"] is True


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_stats_are_derived_and_report_availability(verse_client: TestClient) -> None:
    payload = verse_client.get("/api/v1/audio/stats").json()
    assert payload["total_records"] == 1
    assert payload["by_veda"] == {"RV": 1}
    assert payload["by_availability"] == {"AVAILABLE": 1}
    assert payload["by_scope_type"] == {"MANTRA": 1}
    assert payload["caveats"]


def test_an_empty_catalog_reports_not_built_rather_than_zero_coverage(
    silent_client: TestClient,
) -> None:
    payload = silent_client.get("/api/v1/audio/stats").json()
    assert payload["total_records"] == 0
    assert payload["data_status"] == "NOT_BUILT"


# ---------------------------------------------------------------------------
# The streaming route cannot become an open proxy
# ---------------------------------------------------------------------------


def test_streaming_an_unknown_id_is_a_404(verse_client: TestClient) -> None:
    assert verse_client.get("/api/v1/audio/NOPE:NOPE/stream").status_code == 404


def test_there_is_no_route_that_proxies_an_arbitrary_url() -> None:
    """Section 19: no ``?url=`` parameter may exist anywhere on the audio surface."""
    from vedagraph.api.app import create_app

    spec = create_app().openapi()
    for path, operations in spec["paths"].items():
        if "audio" not in path:
            continue
        for operation in operations.values():
            names = {p["name"] for p in operation.get("parameters", [])}
            assert not names & {"url", "media_url", "src", "source", "target"}, path


def test_a_remote_direct_record_with_no_local_copy_is_a_409() -> None:
    """Not a 404: the record is real and the client needs to be sent to the publisher."""
    app, client, repository = client_for(AudioCatalog([hymn_record()]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([hymn_record()])
        response = client.get("/api/v1/audio/LEGACY:RV:sukta-01-001/stream")
    assert response.status_code == 409
    body = response.json()
    assert body["error"] == "AUDIO_NOT_STREAMABLE"
    assert "example.invalid" in (body["hint"] or "")


def test_a_source_outage_is_a_502_about_audio_not_a_503_about_the_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A third party being down must not look like this product's graph being down."""
    from vedagraph.api.services import audio_service

    def explode(self: Any, veda: str, shlok_id: str) -> tuple[bytes, str]:
        raise TimeoutError("upstream did not answer")

    monkeypatch.setattr(audio_service.VedSearchClient, "audio_bytes", explode)
    app, client, repository = client_for(AudioCatalog([verse_record()]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([verse_record()])
        response = client.get("/api/v1/audio/VEDSEARCH:RV:1.1.1/stream")
    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "AUDIO_SOURCE_UNAVAILABLE"
    assert "vedsearch" not in body["detail"].lower() or "source" in body["detail"].lower()


def test_a_proxied_record_streams_decoded_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vedagraph.api.services import audio_service

    payload = b"ID3\x03" + bytes(range(256)) * 4

    def fake(self: Any, veda: str, shlok_id: str) -> tuple[bytes, str]:
        return payload, "audio/mpeg"

    monkeypatch.setattr(audio_service.VedSearchClient, "audio_bytes", fake)
    audio_service._proxy_cache.clear()
    app, client, repository = client_for(AudioCatalog([verse_record()]))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([verse_record()])
        whole = client.get("/api/v1/audio/VEDSEARCH:RV:1.1.1/stream")
        ranged = client.get(
            "/api/v1/audio/VEDSEARCH:RV:1.1.1/stream", headers={"Range": "bytes=4-13"}
        )
        unsatisfiable = client.get(
            "/api/v1/audio/VEDSEARCH:RV:1.1.1/stream", headers={"Range": "bytes=99999-"}
        )
    assert whole.status_code == 200
    assert whole.content == payload
    assert whole.headers["accept-ranges"] == "bytes"
    assert ranged.status_code == 206
    assert ranged.content == payload[4:14]
    assert ranged.headers["content-range"] == f"bytes 4-13/{len(payload)}"
    assert unsatisfiable.status_code == 416
    assert unsatisfiable.headers["content-range"] == f"bytes */{len(payload)}"


# ---------------------------------------------------------------------------
# Local cache, which takes precedence when present
# ---------------------------------------------------------------------------


@pytest.fixture
def cached_client(tmp_path: Path) -> Iterator[tuple[TestClient, bytes]]:
    payload = bytes(range(256)) * 8
    cache = tmp_path / "audio" / "cache" / "RV"
    cache.mkdir(parents=True)
    (cache / "track.mp3").write_bytes(payload)
    record = verse_record(
        audio_id="VEDSEARCH:RV:cached",
        playback_mode=PlaybackMode.LOCAL_CACHE,
        local_cache_path="RV/track.mp3",
        local_copy_permitted=True,
    )
    app, client, repository = client_for(AudioCatalog([record]), data_dir=tmp_path)
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([record])
        app.state.data_dir = tmp_path
        yield client, payload


def test_a_cached_file_streams_whole(cached_client: tuple[TestClient, bytes]) -> None:
    client, payload = cached_client
    response = client.get("/api/v1/audio/VEDSEARCH:RV:cached/stream")
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers["accept-ranges"] == "bytes"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("bytes=10-19", slice(10, 20)),
        ("bytes=2040-", slice(2040, None)),
        ("bytes=-16", slice(-16, None)),
    ],
)
def test_cached_ranges_return_exactly_those_bytes(
    cached_client: tuple[TestClient, bytes], header: str, expected: slice
) -> None:
    client, payload = cached_client
    response = client.get("/api/v1/audio/VEDSEARCH:RV:cached/stream", headers={"Range": header})
    assert response.status_code == 206
    assert response.content == payload[expected]


@pytest.mark.parametrize("header", ["bytes=99999-", "bytes=-", "kilobytes=0-10", "nonsense"])
def test_an_unsatisfiable_cached_range_is_416_naming_the_real_size(
    cached_client: tuple[TestClient, bytes], header: str
) -> None:
    client, payload = cached_client
    response = client.get("/api/v1/audio/VEDSEARCH:RV:cached/stream", headers={"Range": header})
    assert response.status_code == 416
    assert response.headers["content-range"] == f"bytes */{len(payload)}"


def test_a_missing_cache_file_falls_back_rather_than_breaking_the_player(
    tmp_path: Path,
) -> None:
    """A cache cleared after the catalog was written must not yield a dead stream_url."""
    record = verse_record(
        audio_id="VEDSEARCH:RV:ghost",
        playback_mode=PlaybackMode.LOCAL_CACHE,
        local_cache_path="RV/absent.mp3",
        local_copy_permitted=True,
    )
    app, client, repository = client_for(AudioCatalog([record]), data_dir=tmp_path)
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog([record])
        app.state.data_dir = tmp_path
        playback = client.get("/api/v1/audio/VEDSEARCH:RV:ghost").json()["playback"]
    # Falls back to the remote path, which for this source is the proxied route.
    assert playback["mode"] in {"PROXIED_STREAM", "REMOTE_DIRECT"}
    assert playback["stream_url"] or playback["media_url"]


# ---------------------------------------------------------------------------
# Work route
# ---------------------------------------------------------------------------


def test_work_audio_counts_verses_and_says_so(verse_client: TestClient) -> None:
    payload = verse_client.get("/api/v1/works/VG:WORK:RV:SAK/audio").json()
    assert payload["veda"] == "RV"
    assert payload["recension"] == "SAK"
    assert payload["mapped_scope_count"] == 1
    assert payload["playable_scope_count"] == 1
    assert payload["scope_type_counts"] == {"MANTRA": 1}


def test_work_audio_reports_playable_separately_from_mapped() -> None:
    """A withdrawn recording must not be counted as coverage the reader can hear."""
    records = [
        verse_record(),
        verse_record(
            audio_id="VEDSEARCH:RV:1.1.2",
            scope_key="VG:RV:SAK:M01:S001:V002",
            source_reference="1.1.2",
            availability=Availability.BROKEN,
        ),
    ]
    app, client, repository = client_for(AudioCatalog(records))
    with client:
        app.state.repository = repository
        app.state.audio_catalog = AudioCatalog(records)
        payload = client.get("/api/v1/works/VG:WORK:RV:SAK/audio").json()
    assert payload["mapped_scope_count"] == 2
    assert payload["playable_scope_count"] == 1


def test_work_audio_for_a_veda_with_nothing_is_not_built(verse_client: TestClient) -> None:
    payload = verse_client.get("/api/v1/works/VG:WORK:SV:KAU/audio").json()
    assert payload["tracks"] == []
    assert payload["data_status"] == "NOT_BUILT"
    assert payload["caveats"]


def test_an_unknown_work_is_a_404(verse_client: TestClient) -> None:
    assert verse_client.get("/api/v1/works/VG:WORK:XX:YY/audio").status_code == 404
