"""
Export what each relationship means, for the graph canvases to draw on an edge.

## Why this exists

The World View draws its edges from a build artifact, not from the API: `world.bin` carries a
`edgeType` byte per edge indexing `world.json`'s `edgeTypes`, so the canvas knows that an edge
is a `HAS_RISHI` without asking anyone. What it has never had is the *words* - and a line
between two dots that the reader cannot name is decoration, not knowledge.

The words already exist. `PREDICATE_SEMANTICS` in the graph service is the curated table the
served API reads: every neighbourhood and path edge carries `label=semantics.phrase` from it,
built in one place. The temptation was to write the same table again in TypeScript, and this
repository has twice paid for two copies of one lookup drifting apart. It would have drifted
immediately: the frontend's own `humanizePredicate` - which merely lowercases and replaces
underscores - disagrees with the curated phrasing on 44 of 57 predicates. It says "has rishi"
where the scholarship says "is ascribed to the seer".

So the table is exported rather than retyped. One canonical source in Python, consumed by the
live API and by the offline artifact alike. A phrase can only change in one place.

## The fallback is imported, not reimplemented

`_semantics()` is the API's own degradation for a predicate with no curated entry - it returns
readable words and says plainly that no explanation is curated, rather than raising. It is
imported here for the same reason the table is: so that an uncurated predicate reads the same
on an edge as it does in the API, and `generated_from` records which of the two it came from
so the interface can decline to explain what nobody has explained.

Structural predicates are the reason this matters. `CONTAINS` joins a hymn to its verses and is
drawn in the world, but it is not traversable, so it is deliberately absent from the curated
table. It still needs words when a reader hovers it.

## Direction

Only the ontology's own declaration is exported. `SIGNATURES` marks ten predicates and leaves
forty-seven undeclared, and the honest export of an undeclared predicate is UNDECLARED - not a
guess derived from how the rows happen to be stored. Stored direction is not evidence: the
symmetric predicates are all written one way round with no mirrored row, so an arrowhead drawn
from storage order would assert a direction the corpus does not claim.

Nothing here reads Neo4j, and nothing here writes anything but the output file.

Usage:
    python scripts/export_predicate_semantics.py
    python scripts/export_predicate_semantics.py --check   # verify, change nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from vedagraph.api.services.graph_service import (
    PREDICATE_SEMANTICS,
    TRAVERSABLE_RELATIONSHIPS,
    _semantics,
)
from vedagraph.enrich.predicates import SIGNATURES

REPO = Path(__file__).resolve().parent.parent
WORLD_MANIFEST = REPO / "frontend" / "public" / "world" / "world.json"
#: The public export itself. Hashed here rather than trusted through the manifest.
RAW_EXPORT = REPO / "frontend" / ".world" / "world.raw.json"
DEFAULT_OUT = REPO / "frontend" / "public" / "world" / "world.predicates.json"

#: What the ontology declares about a predicate's direction, and nothing more.
DIRECTED = "DIRECTED"
SYMMETRIC = "SYMMETRIC"
UNDECLARED = "UNDECLARED"


def direction_of(predicate: str) -> str:
    """The declared direction, or an honest admission that there is none.

    `SIGNATURES` is the only place in the codebase that states symmetry, and it states it for
    ten predicates. Inferring the rest from stored row direction would be inventing evidence:
    every symmetric predicate is stored one-directionally with no mirrored row, so storage
    order says nothing about whether the relationship has a direction.
    """
    signature = SIGNATURES.get(predicate)
    if signature is None:
        return UNDECLARED
    return SYMMETRIC if signature.symmetric else DIRECTED


def manifest_edge_types() -> list[str]:
    """The predicates the world artifact actually contains.

    Read from the built manifest rather than from the traversable set, because the artifact is
    the thing being labelled and it holds both less than the ontology (rare predicates that no
    public edge uses) and more (structural predicates the API will not traverse).
    """
    if not WORLD_MANIFEST.exists():
        raise SystemExit(
            f"No world manifest at {WORLD_MANIFEST}. Build the world before exporting the "
            "words for its edges."
        )
    manifest = json.loads(WORLD_MANIFEST.read_text(encoding="utf-8"))
    edge_types = manifest.get("edgeTypes")
    if not isinstance(edge_types, list) or not edge_types:
        raise SystemExit(f"{WORLD_MANIFEST} carries no edgeTypes; it cannot be labelled.")
    return [str(name) for name in edge_types]


def manifest_input_hash() -> str:
    """The public-export hash ``world.json`` was built from, carried through to this file.

    This table is derived from the manifest's ``edgeTypes``, so it inherits the manifest's
    lineage whether or not it records it -- and recording it is the difference between a
    lineage that holds and one that merely happens to. Every other shipped browser artifact
    pins the exact export; this one did not, which left a predicate table that could be
    labelling edge types a different export no longer contains.
    """
    manifest = json.loads(WORLD_MANIFEST.read_text(encoding="utf-8"))
    declared = manifest.get("inputPublicExportHash")
    if not isinstance(declared, str) or not declared:
        raise SystemExit(
            f"{WORLD_MANIFEST} carries no inputPublicExportHash; rebuild the world first so "
            "this table can be pinned to the export it describes."
        )
    # Recomputed, not copied. Reading the manifest's value and re-publishing it would make
    # this file agree with the manifest whatever the manifest said -- a lineage that holds
    # because two files were written by the same run, rather than one anchored to the bytes.
    # If the manifest is stale, this refuses instead of propagating it.
    raw = RAW_EXPORT.read_bytes()
    measured = hashlib.sha256(raw).hexdigest()
    if measured != declared:
        raise SystemExit(
            f"{WORLD_MANIFEST} declares inputPublicExportHash {declared} and "
            f"{RAW_EXPORT} hashes to {measured}. The manifest is stale: rebuild the world "
            "before exporting this table."
        )
    return measured


def build() -> dict[str, object]:
    """Every predicate the product can draw, with the words it is drawn with.

    The union of what the artifact holds and what the API can traverse, so that one payload
    serves the world canvas, the neighbourhood canvas and the path trace without any of them
    needing a second source or a second shape.
    """
    predicates = sorted(set(manifest_edge_types()) | set(TRAVERSABLE_RELATIONSHIPS))

    entries: dict[str, dict[str, str]] = {}
    for predicate in predicates:
        semantics = _semantics(predicate)
        curated = predicate in PREDICATE_SEMANTICS
        entries[predicate] = {
            "phrase": semantics.phrase,
            "asserts": semantics.asserts,
            "limit": semantics.limit,
            "direction": direction_of(predicate),
            # Which of the two sources produced this, so an interface can decline to present
            # an explanation nobody wrote as though a scholar had written it.
            "basis": "CURATED" if curated else "DERIVED_FROM_NAME",
        }

    return {
        "version": 1,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inputPublicExportHash": manifest_input_hash(),
        "source": "vedagraph.api.services.graph_service.PREDICATE_SEMANTICS",
        "counts": {
            "predicates": len(entries),
            "curated": sum(1 for e in entries.values() if e["basis"] == "CURATED"),
            "derived": sum(1 for e in entries.values() if e["basis"] == "DERIVED_FROM_NAME"),
            "symmetric": sum(1 for e in entries.values() if e["direction"] == SYMMETRIC),
            "directed": sum(1 for e in entries.values() if e["direction"] == DIRECTED),
            "undeclared": sum(1 for e in entries.values() if e["direction"] == UNDECLARED),
        },
        "predicates": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report what would be written and whether the file on disk agrees. Writes nothing.",
    )
    args = parser.parse_args()

    payload = build()
    counts = payload["counts"]
    assert isinstance(counts, dict)

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    if args.check:
        if not args.out.exists():
            print(f"MISSING {args.out}")
            return 1
        on_disk = json.loads(args.out.read_text(encoding="utf-8"))
        # `generated` is a timestamp and differs on every run; it is not a drift signal.
        same = on_disk.get("predicates") == payload["predicates"]
        print(f"{'IN SYNC' if same else 'DRIFTED'}  {args.out}")
        return 0 if same else 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered, encoding="utf-8")

    print(f"Wrote {args.out}")
    print(
        f"  {counts['predicates']} predicates: "
        f"{counts['curated']} curated, {counts['derived']} derived from the name"
    )
    print(
        f"  direction: {counts['directed']} directed, {counts['symmetric']} symmetric, "
        f"{counts['undeclared']} undeclared"
    )

    uncurated = sorted(
        name
        for name, entry in payload["predicates"].items()  # type: ignore[union-attr]
        if entry["basis"] == "DERIVED_FROM_NAME"
    )
    if uncurated:
        print(f"  no curated explanation for: {', '.join(uncurated)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
