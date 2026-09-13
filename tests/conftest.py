"""Test configuration: make scripts/ importable for scan-dependent tests."""

import sys
from pathlib import Path

# The scripts that extract, crop, and bind AV scan data import each other as
# sibling modules (crop_atharvaveda_leaf, crop_atharvaveda_line, etc.). Adding
# the scripts directory to sys.path lets importlib-loaded scripts resolve those
# sibling imports without needing the scripts to be packaged.
_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
