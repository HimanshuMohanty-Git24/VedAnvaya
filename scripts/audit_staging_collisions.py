#!/usr/bin/env python3
"""Owner section 12: find where two staged domains would write over each other.

Fourteen domains were produced in parallel by agents that could not see each other's
output. Overlap is expected and mostly harmless -- most domains are keyed by canonical
passage and the corpus is shared. What is not harmless is two domains asserting different
values for the same thing, or two domains minting the same identity independently.

The audit classifies every collision into one of four states, and Wave 3 is barred while
any CONFLICT stands:

  IDENTICAL_DUPLICATE  two domains assert the same value. Import once; no decision needed.
  MERGEABLE            different facets of one subject that compose without contradiction.
  DOMAIN_PRECEDENCE    genuinely different values, but one domain is the authority by
                       construction -- so the rule is recorded rather than the conflict.
  CONFLICT             different values with no principled precedence. Needs a ruling.

A note on what is deliberately NOT flagged. Two domains writing to the same canonical key
is not a collision; the corpus is 20,210 mantras and fourteen domains describe them. Only a
shared *property* with divergent values is. Counting key overlap as collision would produce
tens of thousands of findings and bury the handful that matter -- which is the same failure
as a validator that reports everything and therefore nothing.

Usage:
    python scripts/audit_staging_collisions.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict
from typing import Any

STAGING = pathlib.Path("data/staging")
OUT_DIR = STAGING / "integration"
OUT_FILE = OUT_DIR / "collision_report.json"

#: Properties that carry campaign bookkeeping rather than a claim about the corpus. Two
#: domains both recording their own algorithm_version is not a disagreement.
#:
#: `row_kind` belongs here, and the first run of this audit got that wrong. It reported 11
#: CONFLICTs where the ritual domain said MANTRA_EMPLOYED_IN_RITE and the scholarship domain
#: said SCHOLARLY_DISAGREEMENT for the same mantra -- which are not competing claims at all.
#: Each is a domain's label for the kind of row *it* produced, and the two payloads are
#: otherwise disjoint: ritual carries citing_loci and citing_work_key, scholarship carries
#: position_a and position_b. A mantra can be employed in a rite and be the subject of a
#: disagreement simultaneously.
#:
#: Worth stating rather than quietly fixing, because an audit that manufactures conflicts
#: is worse than one that finds none: it trains the reader to dismiss the output, and the
#: real conflict then passes unread.
PROVENANCE_PROPERTIES = frozenset(
    {
        "row_kind",
        "record_type",
        "layer",
        "predicate",
        "relation",
        "axis",
        "algorithm_version",
        "code_commit",
        "config_hash",
        "source_snapshot",
        "population",
        "processed_count",
        "positive_count",
        "evaluation",
        "note",
        "notes",
        "citation",
        "veda",
        "assessed_population",
        "run",
        "derivation",
        "importable",
    }
)

#: Domains that share one record model by construction. Within a family, a property name
#: means the same thing everywhere, so a divergent value is a precedence question.
#:
#: ACROSS families it is not. The second run of this audit classified 18 `scope_type`
#: collisions as DOMAIN_PRECEDENCE with the audio family authoritative -- which was wrong,
#: and wrong in the direction that loses data. `attribution` writes
#: `scope_type: SINGLE_MANTRA` meaning the scope of an attribution assertion; `audio_av`
#: writes `scope_type: MANTRA` meaning the scope of an audio record. Same name, different
#: concept. Letting audio win would silently overwrite one meaning with another.
#:
#: That is precisely the case owner section 12 names -- "same property name with
#: incompatible meaning" -- and it needs namespacing at import, not a precedence rule.
DOMAIN_FAMILIES: dict[str, str] = {
    "audio_rv": "audio",
    "audio_yv": "audio",
    "audio_av": "audio",
    "samaveda_music": "audio",
}

#: Where two domains IN ONE FAMILY describe the same property, the authority is recorded
#: here rather than left to import order.
PRECEDENCE: dict[str, tuple[str, str]] = {
    "audio_type": ("audio_rv", "the audio domains share one record model; any is authoritative"),
    "availability": ("audio_rv", "same record model across the four audio domains"),
    "licence": ("audio_rv", "same record model across the four audio domains"),
    "local_copy_permitted": ("audio_rv", "same record model across the four audio domains"),
    "audio_id": ("audio_rv", "same record model across the four audio domains"),
    "duration_seconds": ("audio_rv", "same record model across the four audio domains"),
    "end_seconds": ("audio_rv", "same record model across the four audio domains"),
    "start_seconds": ("audio_rv", "same record model across the four audio domains"),
    "last_verified": ("audio_rv", "same record model across the four audio domains"),
    "attribution": ("audio_rv", "same record model across the four audio domains"),
    "location": ("audio_rv", "same record model across the four audio domains"),
    "media_url": ("audio_rv", "same record model across the four audio domains"),
    "performer": ("audio_rv", "same record model across the four audio domains"),
    "patha_type": ("audio_rv", "same record model across the four audio domains"),
    "mapping_confidence": ("audio_rv", "same record model; also checked by the validator"),
    "scope_type": ("audio_rv", "same record model across the four audio domains"),
    "scope_key": ("audio_rv", "same record model across the four audio domains"),
    "source_name": ("audio_rv", "same record model across the four audio domains"),
    "source_page": ("audio_rv", "same record model across the four audio domains"),
    "source_reference": ("audio_rv", "same record model across the four audio domains"),
    "recension": ("audio_rv", "same record model across the four audio domains"),
    "text_verified": ("audio_rv", "same record model across the four audio domains"),
    "playback_mode": ("audio_rv", "same record model across the four audio domains"),
    "checksum": ("audio_rv", "same record model across the four audio domains"),
    "embed_url": ("audio_rv", "same record model across the four audio domains"),
    "local_cache_path": ("audio_rv", "same record model across the four audio domains"),
    "audio_score": ("audio_rv", "same record model across the four audio domains"),
    "title": ("audio_rv", "same record model across the four audio domains"),
    "tradition": ("audio_rv", "same record model across the four audio domains"),
    "mapping_method": ("audio_rv", "same record model; also checked by the validator"),
}

#: Identity-minting fields. Two domains independently minting the same id for different
#: things is the worst collision available, because it is invisible after import.
IDENTITY_FIELDS = (
    "work_key",
    "work_id",
    "supplementary_work_key",
    "citing_work_key",
    "scholar_key",
    "formula_family_id",
    "family_id",
    "role_filler_key",
    "performance_key",
    "performance_urn",
)


def read_rows(domain: pathlib.Path) -> list[dict[str, Any]]:
    path = domain / "rows.jsonl"
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def canonical(value: Any) -> str:
    """A stable, order-insensitive rendering, so key order is not read as disagreement."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT_FILE))
    args = parser.parse_args()

    domains = sorted(
        p.name for p in STAGING.iterdir() if p.is_dir() and (p / "rows.jsonl").exists()
    )

    # (property, canonical_key) -> {domain: rendered value}
    per_property: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    property_owners: dict[str, set[str]] = defaultdict(set)
    key_owners: dict[str, set[str]] = defaultdict(set)
    identities: dict[tuple[str, str], set[str]] = defaultdict(set)
    domain_rows: dict[str, int] = {}

    for name in domains:
        rows = read_rows(STAGING / name)
        domain_rows[name] = len(rows)
        for row in rows:
            key = row.get("canonical_key") or row.get("entity_key")
            if not key:
                continue
            key_owners[key].add(name)
            payload = row.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            for prop, value in payload.items():
                property_owners[prop].add(name)
                if prop in PROVENANCE_PROPERTIES:
                    continue
                per_property[(prop, key)][name] = canonical(value)
                if prop in IDENTITY_FIELDS and isinstance(value, str):
                    identities[(prop, value)].add(name)

    collisions: list[dict[str, Any]] = []

    for (prop, key), by_domain in per_property.items():
        if len(by_domain) < 2:
            continue
        values = set(by_domain.values())
        families = {DOMAIN_FAMILIES.get(d, d) for d in by_domain}
        if len(values) == 1:
            classification = "IDENTICAL_DUPLICATE"
            resolution = "import once; both domains assert the same value"
        elif prop in PRECEDENCE and len(families) == 1:
            winner, why = PRECEDENCE[prop]
            classification = "DOMAIN_PRECEDENCE"
            resolution = f"{winner} is authoritative: {why}"
        elif len(families) > 1:
            classification = "NAME_COLLISION_DIFFERENT_MEANING"
            resolution = (
                f"'{prop}' is used by unrelated domain families "
                f"({', '.join(sorted(families))}) and almost certainly means different "
                f"things in each. Namespace it per domain at import; do NOT resolve by "
                f"precedence, which would overwrite one concept with another"
            )
        else:
            classification = "CONFLICT"
            resolution = "no principled precedence; needs an owner ruling before Wave 3"
        collisions.append(
            {
                "kind": "SHARED_PROPERTY_ON_ONE_SUBJECT",
                "property": prop,
                "subject": key,
                "domains": sorted(by_domain),
                "distinct_values": len(values),
                "classification": classification,
                "resolution": resolution,
                "values": (
                    {d: v[:180] for d, v in sorted(by_domain.items())}
                    if classification in ("CONFLICT", "NAME_COLLISION_DIFFERENT_MEANING")
                    else None
                ),
            }
        )

    for (field, value), owners in identities.items():
        if len(owners) < 2:
            continue
        collisions.append(
            {
                "kind": "DUPLICATE_MINTED_IDENTITY",
                "property": field,
                "subject": value,
                "domains": sorted(owners),
                "distinct_values": 1,
                "classification": "MERGEABLE",
                "resolution": (
                    "two domains reference one identity. Mergeable only if both mean the "
                    "same entity -- verify before import, because a duplicate id is "
                    "invisible afterwards"
                ),
                "values": None,
            }
        )

    by_class = Counter(c["classification"] for c in collisions)
    blocking = ("CONFLICT", "NAME_COLLISION_DIFFERENT_MEANING")
    conflicts = [c for c in collisions if c["classification"] in blocking]

    shared_props = {p: sorted(d) for p, d in property_owners.items() if len(d) > 1}
    multi_key = sum(1 for owners in key_owners.values() if len(owners) > 1)

    report = {
        "schema_version": "1.0",
        "generated_for_wave": 3,
        "domains_audited": domains,
        "domain_row_counts": domain_rows,
        "subjects_touched_by_more_than_one_domain": multi_key,
        "subjects_touched_total": len(key_owners),
        "properties_shared_by_more_than_one_domain": shared_props,
        "collision_counts": dict(by_class),
        "conflict_count": len(conflicts),
        "wave_3_barred": bool(conflicts),
        "note": (
            "Two domains writing the same canonical key is not a collision and is not "
            "counted as one: fourteen domains describe a shared corpus of 20,210 mantras. "
            "Only a shared property with divergent values, or a duplicated minted "
            "identity, is a collision."
        ),
        "collisions": collisions[:4000],
        "collisions_truncated": len(collisions) > 4000,
        "collisions_total": len(collisions),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print(f"  domains audited: {len(domains)}  ({', '.join(domains)})")
    print(f"  subjects touched: {len(key_owners):,}, of which {multi_key:,} by 2+ domains")
    print(f"  properties shared by 2+ domains: {len(shared_props)}")
    print()
    for classification, count in sorted(by_class.items()):
        print(f"  {classification:22} {count:>7,}")
    if not by_class:
        print("  no collisions of any class")
    print()
    if conflicts:
        print(f"  WAVE 3 BARRED -- {len(conflicts)} CONFLICT(s) need an owner ruling:")
        seen_props: set[str] = set()
        for conflict in conflicts:
            prop = str(conflict["property"])
            if prop in seen_props:
                continue
            seen_props.add(prop)
            same = [c for c in conflicts if c["property"] == prop]
            print(f"    {prop}  [{conflict['classification']}]  x{len(same)}")
            print(f"      domains: {', '.join(conflict['domains'])}")
            print(f"      {conflict['resolution']}")

    else:
        print("  CONFLICT = 0. No collision bars Wave 3.")
    print()
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
