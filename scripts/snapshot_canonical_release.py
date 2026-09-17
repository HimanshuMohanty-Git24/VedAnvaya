"""Record a tracked, verifiable fingerprint of an untracked canonical release.

``.gitignore`` excludes ``data/canonical/**`` (line 17), so the released corpus has no git
history: nothing detects a silent truncation, a partial rebuild, or a file deleted by a
stray export. That hazard is recorded as ``SV-UNTRACKED-RELEASE-01`` in
``data/source_registry/four_veda_backlog.jsonl``, and the same class of failure has already
happened once in this project -- the sealed schema was destroyed by a ``schema export`` and
recovered only from a dangling git blob.

Committing the corpus is not the fix. The four released datasets are ~103 MB and the wider
``data/canonical`` tree ~146 MB, most of it JSONL that a rebuild reproduces byte-identically;
and the Rigvedic primary layer is CC BY-NC-SA, which
``data/builds/four_veda_corpus_candidate_manifest.json`` says must not be republished as one
merged adapted work. What a later reader needs is not the bytes but *the identity of the
bytes that shipped*: a per-file digest that is small, tracked, and survives a clone.

So this writes a manifest -- path, size, sha256, mtime -- plus a single ``fingerprint_sha256``
over the sorted ``path\\0size\\0sha256`` lines. The fingerprint deliberately excludes mtime,
because mtime is not preserved by a copy and an external snapshot must be able to reproduce
the same fingerprint as the working tree.

Each release directory already carries its own ``manifest.json`` with per-file hashes, but
that file lives *inside* ``data/canonical/`` and is therefore gitignored too: it is destroyed
by exactly the event it would have detected. The two tracked semantic freezes in
``docs/manifests/`` hash 71 and 67 files, of which only 15 are canonical -- all of them
``rigveda_full_v1``. Nothing tracked covers the Samaveda, the Yajurveda or the Atharvaveda.

Tiers
-----
``RELEASE``
    The four directories the product actually projects, read from
    :data:`vedagraph.graph.projection.CANONICAL_DIRS` rather than restated here, so the
    manifest cannot silently drift from what the graph loads.
``CANONICAL_OTHER``
    Everything else under ``data/canonical/`` -- pilots, provisional builds, and the
    per-mandala partial Rigveda builds the full build supersedes. Hashed and recorded, but
    reported separately, because the closure test is about *released* artifacts.

Usage
-----
    python scripts/snapshot_canonical_release.py                 # write the manifest
    python scripts/snapshot_canonical_release.py --verify        # check the tree against it
    python scripts/snapshot_canonical_release.py --snapshot DIR  # also copy the release out
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import sys
from dataclasses import asdict, dataclass
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CANONICAL_ROOT = PROJECT_ROOT / "data" / "canonical"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "staging"
    / "final_closure_sprint"
    / "agent6"
    / "gap005_canonical_release_manifest.json"
)

MANIFEST_VERSION = "canonical-release-manifest-v1"

TIER_RELEASE = "RELEASE"
TIER_OTHER = "CANONICAL_OTHER"

#: Files that are not corpus content and whose presence says nothing about release identity.
_SKIP_NAMES = frozenset({".gitkeep"})

_READ_CHUNK = 1 << 20


def released_dirs() -> dict[str, str]:
    """The four projected release directories, keyed by Veda code.

    Imported rather than restated: if a later build renames a release directory,
    ``CANONICAL_DIRS`` is the single place that changes and this manifest follows it.
    """
    src = PROJECT_ROOT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from vedagraph.graph.projection import CANONICAL_DIRS

    return dict(CANONICAL_DIRS)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_READ_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Entry:
    path: str
    tier: str
    dataset: str
    size: int
    sha256: str
    mtime: str


def _mtime(path: pathlib.Path) -> str:
    stamp = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def walk(root: pathlib.Path = CANONICAL_ROOT) -> list[Entry]:
    """Hash every file under ``root``, tiering each by whether the product projects it."""
    release = {name for name in released_dirs().values()}
    entries: list[Entry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in _SKIP_NAMES:
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        dataset = path.relative_to(root).parts[0] if path.parent != root else ""
        entries.append(
            Entry(
                path=rel,
                tier=TIER_RELEASE if dataset in release else TIER_OTHER,
                dataset=dataset,
                size=path.stat().st_size,
                sha256=sha256_file(path),
                mtime=_mtime(path),
            )
        )
    return sorted(entries, key=lambda e: e.path)


def fingerprint(entries: list[dict[str, Any]] | list[Entry]) -> str:
    """A single digest over ``path\\0size\\0sha256``, sorted by path.

    mtime is excluded on purpose. A copy does not carry it, and an external snapshot that
    holds identical bytes must be able to prove that by reproducing this value.
    """
    rows = [asdict(e) if isinstance(e, Entry) else e for e in entries]
    payload = "\n".join(
        f"{r['path']}\0{r['size']}\0{r['sha256']}" for r in sorted(rows, key=lambda r: r["path"])
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(entries: list[Entry]) -> dict[str, Any]:
    rows = [asdict(e) for e in entries]
    by_tier: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_tier.setdefault(row["tier"], {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += row["size"]
    release_rows = [r for r in rows if r["tier"] == TIER_RELEASE]
    return {
        "manifest_version": MANIFEST_VERSION,
        "backlog_id": "SV-UNTRACKED-RELEASE-01",
        "gap_id": "GAP-PRODUCT_SURFACE-005",
        "generated_at": dt.datetime.now(tz=dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "canonical_root": CANONICAL_ROOT.relative_to(PROJECT_ROOT).as_posix(),
        "gitignore_rule": "data/canonical/** (.gitignore line 17)",
        "released_datasets": released_dirs(),
        "tier_totals": by_tier,
        "file_count": len(rows),
        "total_bytes": sum(r["size"] for r in rows),
        "release_file_count": len(release_rows),
        "release_total_bytes": sum(r["size"] for r in release_rows),
        "fingerprint_sha256": fingerprint(rows),
        "release_fingerprint_sha256": fingerprint(release_rows),
        "entries": rows,
    }


def write_manifest(path: pathlib.Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = build_manifest(walk())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify(
    manifest: dict[str, Any],
    root: pathlib.Path = PROJECT_ROOT,
    tiers: frozenset[str] = frozenset({TIER_RELEASE, TIER_OTHER}),
) -> dict[str, Any]:
    """Re-hash the tree and report every way it differs from the manifest.

    Returns a result dict rather than raising, so a caller can report *all* of the damage
    instead of the first file that happened to sort first.
    """
    recorded = manifest.get("fingerprint_sha256")
    rows = [r for r in manifest.get("entries", []) if r["tier"] in tiers]
    missing: list[str] = []
    mismatched: list[dict[str, Any]] = []
    for row in rows:
        path = root / row["path"]
        if not path.is_file():
            missing.append(row["path"])
            continue
        actual = sha256_file(path)
        if actual != row["sha256"]:
            mismatched.append(
                {
                    "path": row["path"],
                    "expected_sha256": row["sha256"],
                    "actual_sha256": actual,
                    "expected_size": row["size"],
                    "actual_size": path.stat().st_size,
                }
            )
    return {
        "checked": len(rows),
        "missing": missing,
        "mismatched": mismatched,
        "recomputed_fingerprint_sha256": fingerprint(manifest.get("entries", [])),
        "recorded_fingerprint_sha256": recorded,
        "internally_consistent": fingerprint(manifest.get("entries", [])) == recorded,
        "ok": not missing and not mismatched,
    }


def snapshot(
    destination: pathlib.Path,
    manifest: dict[str, Any],
    tiers: frozenset[str] = frozenset({TIER_RELEASE}),
) -> dict[str, Any]:
    """Copy the listed files to ``destination``, preserving their repo-relative layout."""
    rows = [r for r in manifest["entries"] if r["tier"] in tiers]
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for row in rows:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / row["path"], target)
        copied += 1
    result = verify(manifest, root=destination, tiers=tiers)
    result["destination"] = str(destination)
    result["copied"] = copied
    result["snapshot_fingerprint_sha256"] = fingerprint(rows)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="check the tree, write nothing")
    parser.add_argument("--snapshot", type=pathlib.Path, help="also copy the RELEASE tier here")
    parser.add_argument("--manifest", type=pathlib.Path, default=MANIFEST_PATH)
    args = parser.parse_args(argv)

    if args.verify:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = verify(manifest)
        print(json.dumps({k: v for k, v in result.items() if k != "entries"}, indent=2))
        return 0 if result["ok"] and result["internally_consistent"] else 1

    manifest = write_manifest(args.manifest)
    print(
        json.dumps(
            {
                "manifest": str(args.manifest.relative_to(PROJECT_ROOT)),
                "file_count": manifest["file_count"],
                "total_bytes": manifest["total_bytes"],
                "release_file_count": manifest["release_file_count"],
                "release_total_bytes": manifest["release_total_bytes"],
                "tier_totals": manifest["tier_totals"],
                "fingerprint_sha256": manifest["fingerprint_sha256"],
                "release_fingerprint_sha256": manifest["release_fingerprint_sha256"],
            },
            indent=2,
        )
    )
    if args.snapshot:
        result = snapshot(args.snapshot, manifest)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
