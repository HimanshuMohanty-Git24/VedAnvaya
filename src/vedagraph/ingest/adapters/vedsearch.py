"""VedSearch discovery stub; counts and translations remain source assertions."""

from pathlib import Path

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord


class VedSearchAdapter(SourceAdapter):
    source_id = "VEDSEARCH"

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        if scope != "RV.1.1":
            return []
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url="https://vedsearch.org/rigved/1/1/1",
                locator="RV 1.1.1",
                media_type="text/html",
            )
        ]

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        raise NotImplementedError(
            "VedSearch parsing awaits documented API/HTML stability and numbering verification"
        )
