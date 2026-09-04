"""Pin the ten VedaWeb book TEI snapshots that carry the Zurich morphology layer.

The morphology is not a separate download: it is the ``zurich`` annotation layer inside
the VedaWeb book TEI artifacts this project already pinned at commit ``d3eb8af``. This
script writes the index the lexical build reads, so the build never scans a mutable
directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAW_ROOT = Path("data/raw/vedaweb")
OUTPUT = Path("data/derived/vedaweb_morphology_artifacts.json")
COMMIT = "d3eb8af7324338161520d2d35eae8f7e985a19a5"
BOOK_RE = re.compile(r"rv_book_(\d{2})\.tei$")


def main() -> int:
    entries: dict[int, dict[str, object]] = {}
    for metadata_path in sorted(RAW_ROOT.glob("*/*.metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        url = str(metadata.get("retrieval_url", ""))
        match = BOOK_RE.search(url)
        if match is None or COMMIT not in url:
            continue
        mandala = int(match.group(1))
        snapshot = metadata_path.with_suffix("").with_suffix(".tei")
        entries[mandala] = {
            "mandala": mandala,
            "artifact_id": f"VEDAWEB.RV.BOOK{mandala:02d}.TEI.D3EB8AF",
            "filename": f"rv_book_{mandala:02d}.tei",
            "snapshot_path": snapshot.as_posix(),
            "snapshot_id": str(metadata["snapshot_id"]),
            "sha256": str(metadata["sha256"]),
            "size": snapshot.stat().st_size,
            "url": url,
        }
    missing = sorted(set(range(1, 11)) - set(entries))
    if missing:
        raise SystemExit(f"missing pinned VedaWeb book snapshots for mandalas: {missing}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps([entries[m] for m in sorted(entries)], indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"pinned {len(entries)} book artifacts at commit {COMMIT[:7]} -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
