from datetime import UTC, datetime
from pathlib import Path

from vedagraph.ingest.fetcher import content_sha256, persist_snapshot


def test_raw_snapshot_hash_and_immutable_layout(tmp_path: Path) -> None:
    content = b"fixture bytes"
    timestamp = datetime(2026, 9, 4, tzinfo=UTC)
    result = persist_snapshot(
        data_dir=tmp_path,
        source_id="GRETIL",
        url="https://example.test/rv.xml",
        content=content,
        content_type="application/xml",
        retrieved_at=timestamp,
    )
    assert result.metadata.sha256 == content_sha256(content)
    assert result.content_path.read_bytes() == content
    assert result.content_path.parent == tmp_path / "raw" / "gretil" / "2026-09-04"
    again = persist_snapshot(
        data_dir=tmp_path,
        source_id="GRETIL",
        url="https://example.test/rv.xml",
        content=content,
        content_type="application/xml",
        retrieved_at=timestamp,
    )
    assert again.content_path == result.content_path
