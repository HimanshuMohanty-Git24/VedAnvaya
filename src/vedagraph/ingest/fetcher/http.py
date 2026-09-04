"""Conservative HTTP retrieval into immutable raw snapshots."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

import httpx
import orjson
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from vedagraph.config import Settings
from vedagraph.models import RawSnapshotMetadata

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotResult:
    metadata: RawSnapshotMetadata
    content_path: Path
    metadata_path: Path
    reused: bool


def content_sha256(content: bytes) -> str:
    return sha256(content).hexdigest()


def _retryable(error: BaseException) -> bool:
    if isinstance(error, httpx.TransportError):
        return True
    return isinstance(error, httpx.HTTPStatusError) and error.response.status_code >= 500


class PoliteFetcher:
    """Fetch one resource at a time per host with bounded global concurrency."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_next_request: dict[str, float] = {}

    async def _rate_limit(self, host: str) -> None:
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            wait_for = max(0.0, self._host_next_request.get(host, now) - now)
            if wait_for:
                await asyncio.sleep(wait_for)
            self._host_next_request[host] = time.monotonic() + (
                1.0 / self.settings.requests_per_second
            )

    def _find_cached(self, source_id: str, url: str) -> SnapshotResult | None:
        root = self.settings.data_dir / "raw" / source_id.lower()
        if not root.exists():
            return None
        for metadata_path in sorted(root.glob("**/*.metadata.json"), reverse=True):
            try:
                metadata = RawSnapshotMetadata.model_validate_json(metadata_path.read_bytes())
            except (OSError, ValueError):
                continue
            content_path = metadata_path.with_name(metadata.filename)
            if str(metadata.retrieval_url) == url and content_path.exists():
                if content_sha256(content_path.read_bytes()) == metadata.sha256:
                    return SnapshotResult(metadata, content_path, metadata_path, reused=True)
        return None

    async def fetch(self, source_id: str, url: str, *, force: bool = False) -> SnapshotResult:
        if not force and (cached := self._find_cached(source_id, url)) is not None:
            LOGGER.info("snapshot_reused source_id=%s url=%s", source_id, url)
            return cached

        host = urlparse(url).hostname
        if not host:
            raise ValueError(f"URL has no host: {url}")

        timeout = httpx.Timeout(
            connect=self.settings.connect_timeout_seconds,
            read=self.settings.read_timeout_seconds,
            write=self.settings.read_timeout_seconds,
            pool=self.settings.connect_timeout_seconds,
        )
        headers = {"User-Agent": self.settings.effective_user_agent, "Accept": "*/*"}
        partial_dir = self.settings.data_dir / "raw" / ".partial" / source_id.lower()
        partial_dir.mkdir(parents=True, exist_ok=True)
        url_digest = sha256(url.encode("utf-8")).hexdigest()
        partial_path = partial_dir / f"{url_digest}.part"

        async with self._semaphore:
            await self._rate_limit(host)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(4),
                    wait=wait_exponential(multiplier=1, min=1, max=8),
                    retry=retry_if_exception(_retryable),
                    reraise=True,
                ):
                    with attempt:
                        LOGGER.info("snapshot_fetch source_id=%s url=%s", source_id, url)
                        existing_size = partial_path.stat().st_size if partial_path.exists() else 0
                        request_headers = dict(headers)
                        if existing_size:
                            request_headers["Range"] = f"bytes={existing_size}-"
                        async with client.stream("GET", url, headers=request_headers) as response:
                            response.raise_for_status()
                            append = existing_size > 0 and response.status_code == 206
                            mode = "ab" if append else "wb"
                            with partial_path.open(mode) as handle:
                                async for chunk in response.aiter_bytes():
                                    handle.write(chunk)
                            response_url = str(response.url)
                            response_status = response.status_code
                            response_headers = dict(response.headers)
                content = partial_path.read_bytes()
                result = persist_snapshot(
                    data_dir=self.settings.data_dir,
                    source_id=source_id,
                    url=response_url,
                    content=content,
                    http_status=response_status,
                    content_type=response_headers.get("content-type"),
                    etag=response_headers.get("etag"),
                    last_modified=response_headers.get("last-modified"),
                    request_headers={"user-agent": headers["User-Agent"]},
                )
                partial_path.unlink(missing_ok=True)
                return result
        raise RuntimeError("unreachable")


def persist_snapshot(
    *,
    data_dir: Path,
    source_id: str,
    url: str,
    content: bytes,
    http_status: int = 200,
    content_type: str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    request_headers: dict[str, str] | None = None,
    retrieved_at: datetime | None = None,
) -> SnapshotResult:
    """Persist bytes once; content-addressed names make reruns idempotent."""
    timestamp = retrieved_at or datetime.now(UTC)
    digest = content_sha256(content)
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or _suffix_for(content_type)
    filename = f"{digest}{suffix}"
    target_dir = data_dir / "raw" / source_id.lower() / timestamp.date().isoformat()
    target_dir.mkdir(parents=True, exist_ok=True)
    content_path = target_dir / filename
    metadata_path = target_dir / f"{digest}.metadata.json"
    if content_path.exists() and content_path.read_bytes() != content:
        raise RuntimeError(f"hash collision or corrupt snapshot at {content_path}")
    if not content_path.exists():
        content_path.write_bytes(content)
    metadata = RawSnapshotMetadata(
        snapshot_id=f"{source_id}:{digest}",
        source_id=source_id,
        retrieval_url=url,
        retrieved_at=timestamp,
        http_status=http_status,
        content_type=content_type,
        sha256=digest,
        etag=etag,
        last_modified=last_modified,
        filename=filename,
        request_headers=request_headers or {},
        parser_independent_metadata={"host": parsed.hostname or ""},
    )
    encoded = (
        orjson.dumps(
            metadata.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    if not metadata_path.exists():
        metadata_path.write_bytes(encoded)
    return SnapshotResult(metadata, content_path, metadata_path, reused=False)


def _suffix_for(content_type: str | None) -> str:
    if content_type and "xml" in content_type:
        return ".xml"
    if content_type and "json" in content_type:
        return ".json"
    if content_type and "html" in content_type:
        return ".html"
    return ".bin"
