"""Shared HTTP identity for the audio tools.

One constant, in one place, because three separate tools talk to the same third party and
an operator reading their access log should see a single recognisable agent rather than
three. It names the project as a local research tool and carries a URL, so whoever runs
that server can tell what the traffic is and who to contact about it.
"""

from typing import Final

USER_AGENT: Final = "VedaGraph/1.0 (local research tool; +https://github.com/vedagraph/vedagraph)"

__all__ = ["USER_AGENT"]
