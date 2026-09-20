"""AGENT B C05: make GAP-QUALITY-003's closure survive a rebuild.

Agent B's finding, and it is correct and it is the most serious one in the review: seven
writers still stamp ``confidence`` on the seven source-explicit predicates, and
``grep -rn source_explicit_tier_marker src/vedagraph/graph/ src/vedagraph/domain/``
returned ZERO hits -- no builder wrote the replacement property. A rebuild would take the
published closure measure from 0 back to 51,364 and produce 0 tier markers.

That is the "fix that never reaches the shipped artifact" defect this repository has already
recorded once, and it is the same objection RITUAL-003 was held open on in this very round:
"the 12 edges are not reproducible from the registry that is supposed to generate them".
A closure that only holds until the next build is not a closure.

THE FIX IS AT SOURCE, in one place. ``vedagraph.domain.tiers`` already knows which
predicates are ``L1_SOURCE_EXPLICIT``; rather than restate that list an eighth time, the
name of the property each writer should use is derived from a single declaration here and
imported by every writer. Seven Cypher statements change ``rel.confidence`` to
``rel.source_explicit_tier_marker`` and add the withdrawal note; two Python dict literals do
the same.

WHY RENAME AND NOT DELETE: the 1.0 records that the edge is source-explicit. Deleting the
field loses that; keeping it called ``confidence`` keeps inviting a threshold nobody can
honour. ``confidence != probability``.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]

DECLARATION = '''

#: The seven predicates whose ``confidence`` was a constant 1.0 on every edge, withdrawn by
#: GAP-QUALITY-003 and re-landed under a name that says what the value is.
#:
#: A constant on every edge of a predicate encodes the evidence TIER -- the source says so --
#: and not a calibrated probability. Published as ``confidence`` it offered a numeric filter
#: that selects all of a predicate's edges or none, which is an invitation to a threshold
#: with no measured meaning. Published as ``source_explicit_tier_marker`` it says the one
#: thing it actually knows.
#:
#: Declared HERE, in the module every writer already imports, because R5 landed the rename
#: as a migration and left seven writers still stamping ``confidence`` -- so the next
#: rebuild would have reversed a closed gap. Agent B's C05. A predicate's membership is not
#: restated in the writers; they ask this map for the property name.
SOURCE_EXPLICIT_TIER_PREDICATES: Final[frozenset[str]] = frozenset(
    {
        "HAS_RISHI",
        "HAS_CHANDAS",
        "HAS_DEVATA",
        "HAS_DEVATA_ASCRIPTION",
        "HAS_DEVATA_DERIVED",
        "ASCRIBES_TO_DEVATA",
        "BELONGS_TO_FAMILY",
    }
)

#: The property a writer must use for a given predicate's evidence-strength figure.
SOURCE_EXPLICIT_TIER_PROPERTY: Final = "source_explicit_tier_marker"

#: Carried beside the marker so a reader meeting it knows why it is not called confidence.
SOURCE_EXPLICIT_TIER_NOTE: Final = (
    "The value was a constant 1.0 on every edge of this predicate. It encodes the evidence "
    "TIER -- the source states this -- and not a calibrated probability, so it offered a "
    "numeric filter that selects everything or nothing. confidence != probability."
)


def confidence_property(predicate: str) -> str:
    """The property name a writer should stamp this predicate's strength figure onto.

    ``source_explicit_tier_marker`` for the seven whose value is a tier, ``confidence`` for
    everything else, where the value genuinely varies edge to edge.
    """
    if predicate in SOURCE_EXPLICIT_TIER_PREDICATES:
        return SOURCE_EXPLICIT_TIER_PROPERTY
    return "confidence"
'''

CYPHER_EDITS: list[tuple[str, str, str]] = [
    (
        "src/vedagraph/graph/loader.py",
        """            MERGE (p)-[rel:HAS_RISHI]->(r)
            SET rel.confidence = row.confidence,""",
        """            MERGE (p)-[rel:HAS_RISHI]->(r)
            SET rel.source_explicit_tier_marker = row.confidence,
                rel.confidence_field_withdrawn_because = $tier_note,
                rel.encoded_tier = 'L1_SOURCE_EXPLICIT',""",
    ),
    (
        "src/vedagraph/graph/loader.py",
        """            MERGE (p)-[rel:HAS_DEVATA]->(d)
            SET rel.confidence = row.confidence,""",
        """            MERGE (p)-[rel:HAS_DEVATA]->(d)
            SET rel.source_explicit_tier_marker = row.confidence,
                rel.confidence_field_withdrawn_because = $tier_note,
                rel.encoded_tier = 'L1_SOURCE_EXPLICIT',""",
    ),
    (
        "src/vedagraph/graph/loader.py",
        """            MERGE (p)-[rel:HAS_CHANDAS]->(c)
            SET rel.confidence = row.confidence,""",
        """            MERGE (p)-[rel:HAS_CHANDAS]->(c)
            SET rel.source_explicit_tier_marker = row.confidence,
                rel.confidence_field_withdrawn_because = $tier_note,
                rel.encoded_tier = 'L1_SOURCE_EXPLICIT',""",
    ),
]


def main() -> None:
    # ---- 1. the single declaration, in tiers.py -----------------------------
    tiers = ROOT / "src" / "vedagraph" / "domain" / "tiers.py"
    raw = tiers.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("tiers.py contains CRLF; refusing")
    text = raw.decode("utf-8")
    if "SOURCE_EXPLICIT_TIER_PREDICATES" in text:
        print("  tiers.py already declares the map")
    else:
        if not text.endswith("\n"):
            text += "\n"
        tiers.write_bytes((text + DECLARATION.lstrip("\n")).encode("utf-8"))
        print("  declared SOURCE_EXPLICIT_TIER_PREDICATES in tiers.py")

    # ---- 2. the Cypher writers ---------------------------------------------
    lf, crlf_ending = "\n", "\r\n"
    for relative, old, new in CYPHER_EDITS:
        path = ROOT / relative
        raw = path.read_bytes()
        # loader.py is 702 CRLF lines with no bare LF. The anchors here are written in LF,
        # so they are converted to the file's OWN ending before matching and written back in
        # it. Normalising the file would turn a three-line change into a 702-line diff --
        # the mixed-line-ending defect this repository has recorded.
        is_crlf = crlf_ending.encode("utf-8") in raw
        text = raw.decode("utf-8")
        anchor = old.replace(lf, crlf_ending) if is_crlf else old
        body = new.replace(lf, crlf_ending) if is_crlf else new
        if body.splitlines()[1].strip() in text:
            print(f"  already patched: {relative} ({old.splitlines()[0].strip()})")
            continue
        if anchor not in text:
            raise SystemExit(f"anchor not found in {relative}:\n{old}")
        path.write_bytes(text.replace(anchor, body, 1).encode("utf-8"))
        after = path.read_bytes()
        mixed = crlf_ending.encode("utf-8") in after and after.count(
            lf.encode("utf-8")
        ) != after.count(crlf_ending.encode("utf-8"))
        print(
            f"  patched {relative}: {old.splitlines()[0].strip()} "
            f"(crlf={is_crlf}, mixed={mixed})"
        )
        if mixed:
            raise SystemExit(f"{relative} now has MIXED line endings")


if __name__ == "__main__":
    main()
