"""Traditional-metadata scope extraction and review."""

from vedagraph.metadata.ranges import (
    PARSER_VERSION,
    parse_metadata_value,
    parse_range_value,
)
from vedagraph.metadata.review import (
    candidates_from_assertions,
    candidates_from_qa,
    render_review,
    write_review,
)

__all__ = [
    "PARSER_VERSION",
    "candidates_from_assertions",
    "candidates_from_qa",
    "parse_metadata_value",
    "parse_range_value",
    "render_review",
    "write_review",
]
