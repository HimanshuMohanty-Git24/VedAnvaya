"""Source adapter implementations."""

from vedagraph.ingest.adapters.anukramani import WSC2023AnukramaniAdapter
from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.ingest.adapters.gretil import GRETILAdapter
from vedagraph.ingest.adapters.vedaweb import VedaWebAdapter, VedaWebCorpusHeader
from vedagraph.ingest.adapters.vedsearch import VedSearchAdapter
from vedagraph.ingest.adapters.vhp import VHPAdapter
from vedagraph.ingest.adapters.wikisource import WikisourceTranslationAdapter

__all__ = [
    "DiscoveredResource",
    "GRETILAdapter",
    "SourceAdapter",
    "VHPAdapter",
    "VedSearchAdapter",
    "VedaWebAdapter",
    "VedaWebCorpusHeader",
    "WSC2023AnukramaniAdapter",
    "WikisourceTranslationAdapter",
]
