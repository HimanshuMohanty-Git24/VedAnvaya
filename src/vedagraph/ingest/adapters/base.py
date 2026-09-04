"""Source adapter boundary: adapters may create staging records, never canonical records."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from vedagraph.ingest.fetcher import PoliteFetcher, SnapshotResult
from vedagraph.models import StagingTextRecord


@dataclass(frozen=True)
class DiscoveredResource:
    source_id: str
    url: str
    locator: str
    media_type: str


class SourceAdapter(ABC):
    source_id: str

    @abstractmethod
    async def discover(self, scope: str) -> list[DiscoveredResource]:
        """Discover a bounded set of resources for an explicit scope."""

    async def fetch(self, resource: DiscoveredResource, fetcher: PoliteFetcher) -> SnapshotResult:
        if resource.source_id != self.source_id:
            raise ValueError("resource source_id does not match adapter")
        return await fetcher.fetch(self.source_id, resource.url)

    @abstractmethod
    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        """Parse an immutable snapshot into source-specific staging records."""

    def to_staging_records(
        self, snapshot_path: Path, *, snapshot_id: str
    ) -> list[StagingTextRecord]:
        return self.parse(snapshot_path, snapshot_id=snapshot_id)
