"""VedaGraph: a provenance-aware knowledge graph of the four Vedas, and the product over it.

:data:`__version__` is the one place the product version is written. The API's OpenAPI
document, its ``/health`` payload and the packaging metadata all read it from here --
before Product V1 they disagreed, with ``pyproject.toml`` on 0.1.0 and two string literals
in the app factory on 1.0.0, which is the shape that makes a deployed version untrustworthy.
"""

from typing import Final

__version__: Final = "1.0.0"

#: What to call this release in prose, for a UI or a report header.
PRODUCT_NAME: Final = "VedaGraph Product V1"

__all__ = ["PRODUCT_NAME", "__version__"]
