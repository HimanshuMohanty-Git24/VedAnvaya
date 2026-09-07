"""Build the Samaveda referent migration ledger.

Every Samaveda canonical key changes in this run, because the key shape changed: the
contested four-sibling arcika ordinal is replaced by the collection's own name, the ardha
level is dropped from the collections that do not declare one, and the literal ``0`` that
encoded an absent level is gone. This ledger records that, per key, with evidence.

Nothing here is described as backwards compatible. Where a referent changed, the key means
something else, and that is a breaking change even where the UUID is unchanged -- which for
the shape change it is not, since the URN changed too.

Written to ``data/source_registry/`` rather than ``data/derived/``: ``data/derived/**`` is
gitignored, and a migration ledger that is not committed cannot license anything.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from vedagraph.identity import (  # noqa: E402
    SamavedaCollection,
    sv_container_identity,
    sv_mantra_identity,
)
from vedagraph.models import ReferentMigration  # noqa: E402
from vedagraph.referent import MigrationClass  # noqa: E402
from vedagraph.storage.jsonl import write_jsonl  # noqa: E402

PILOT_PASSAGES = REPO / "data" / "canonical" / "samaveda_pilot_v1" / "passages.jsonl"
OUT_PATH = REPO / "data" / "source_registry" / "samaveda_referent_migrations.jsonl"
RUN = "SAMAVEDA_REFERENT_INTEGRITY_REPAIR"
WORK_ID = "VG:WORK:SV:KAU"

OLD_ARCIKA_TO_COLLECTION = {
    1: SamavedaCollection.CHANDA,
    2: SamavedaCollection.ARANYA,
    3: SamavedaCollection.MAHANAMNYA,
    4: SamavedaCollection.UTTARA,
}

_OLD_MANTRA = re.compile(r"^VG:SV:KAU:A(\d+):P(\d+):R(\d+):D(\d+):V(\d+)$")
_OLD_CONTAINER = re.compile(r"^VG:SV:KAU:A(\d+)(?::P(\d+))?(?::R(\d+))?(?::D(\d+))?$")

# The referent defects the count ledger measured on the rejected witness, whose repair the
# selected witness independently confirms. Keys here changed WHAT THEY DENOTE, not merely
# their spelling, so they are recorded as corrections rather than reassignments.
WELDED_KEYS: dict[str, dict[str, str]] = {
    "VG:SV:KAU:A4:P01:R1:D06:V03": {
        "markers": "666, 667, 668",
        "evidence": "the key held a concatenative weld of three printed verses (197 "
        "characters against a 66-character constituent). The selected witness prints "
        "666/667/668 as three separate verses at V01/V02/V03 of the same dasati, so the "
        "repaired key denotes 668 alone.",
    },
    "VG:SV:KAU:A4:P05:R2:D06:V03": {
        "markers": "1282, 1288",
        "evidence": "a displaced line block in the rejected witness put two printed "
        "verses on one address. The selected witness prints them at distinct addresses.",
    },
    "VG:SV:KAU:A4:P05:R2:D10:V01": {
        "markers": "1307, 1308, 1309",
        "evidence": "the rejected witness's verse-index field stuck at 01, absorbing "
        "three printed verses onto one address. The selected witness prints V01/V02/V03.",
    },
    "VG:SV:KAU:A4:P05:R2:D07:V04": {
        "markers": "1283, 1295",
        "evidence": "displaced line block; not materialized in the pilot sample.",
    },
    "VG:SV:KAU:A4:P05:R2:D08:V05": {
        "markers": "1284, 1302",
        "evidence": "displaced line block; not materialized in the pilot sample.",
    },
    "VG:SV:KAU:A4:P08:R2:D08:V02": {
        "markers": "1679, 1680",
        "evidence": "pada label off by one in the rejected witness; not materialized in "
        "the pilot sample.",
    },
}

PHANTOM_KEY = "VG:SV:KAU:A4:P04:R2:D01:V13"


def new_mantra(old_key: str) -> tuple[str, str, str] | None:
    match = _OLD_MANTRA.match(old_key)
    if match is None:
        return None
    arcika, prapathaka, ardha, dasati, verse = (int(v) for v in match.groups())
    collection = OLD_ARCIKA_TO_COLLECTION.get(arcika)
    if collection is None:
        return None
    kwargs: dict[str, int | None] = {}
    if collection is SamavedaCollection.CHANDA:
        # The ardha slot is dropped: the selected witness declares no ardha in this
        # collection and the dasati already numbers 1..10 continuously across the
        # prapathaka, so the old R slot carried no information.
        kwargs = {"prapathaka": prapathaka, "dasati": dasati}
    elif collection is SamavedaCollection.ARANYA:
        kwargs = {"dasati": dasati}
    elif collection is SamavedaCollection.MAHANAMNYA:
        kwargs = {}
    else:
        kwargs = {"prapathaka": prapathaka, "ardha": ardha, "dasati": dasati}
    key, urn, uuid_value = sv_mantra_identity(collection, verse=verse, **kwargs)
    return key, urn, str(uuid_value)


def new_container(old_key: str) -> tuple[str, str, str] | None:
    match = _OLD_CONTAINER.match(old_key)
    if match is None:
        return None
    arcika = int(match.group(1))
    collection = OLD_ARCIKA_TO_COLLECTION.get(arcika)
    if collection is None:
        return None
    prapathaka = int(match.group(2)) if match.group(2) else None
    ardha = int(match.group(3)) if match.group(3) else None
    dasati = int(match.group(4)) if match.group(4) else None
    kwargs: dict[str, int | None] = {}
    if collection is SamavedaCollection.CHANDA:
        kwargs = {"prapathaka": prapathaka or None, "dasati": dasati or None}
    elif collection is SamavedaCollection.ARANYA:
        kwargs = {"dasati": dasati or None}
    elif collection is SamavedaCollection.MAHANAMNYA:
        kwargs = {}
    else:
        kwargs = {
            "prapathaka": prapathaka or None,
            "ardha": ardha or None,
            "dasati": dasati or None,
        }
    # Drop any level whose value the old scheme wrote as 0, which meant "absent here".
    ordered = ("prapathaka", "ardha", "dasati")
    seen_none = False
    for name in ordered:
        if name not in kwargs:
            continue
        if kwargs[name] is None:
            seen_none = True
        elif seen_none:
            kwargs[name] = None
    key, urn, uuid_value = sv_container_identity(collection, **kwargs)
    return key, urn, str(uuid_value)


def main() -> None:
    migrations: list[ReferentMigration] = []

    # 1. The scheme-level record. One entry, so the reason for 139 per-key rows is stated
    #    once rather than repeated 139 times.
    migrations.append(
        ReferentMigration(
            migration_class=MigrationClass.KEY_REASSIGNED_BEFORE_FREEZE.value,
            work_id=WORK_ID,
            reason=(
                "The Samaveda candidate key encoded the contested four-sibling arcika "
                "arity as a bare ordinal in its top slot. That ordinal does not denote a "
                "stable collection: slot-1 value 2 means Aranyarcika in the Pandey e-text "
                "lineage and Uttararcika in every one of the six independent witnesses, a "
                "1,225-verse referent collision. The repaired key names the collection "
                "instead, which every witness including the rejected one agrees on."
            ),
            evidence=(
                "Measured on the full selected corpus: collection assignment agrees "
                "between the two lineages for 1,867 of 1,867 comparable printed verse "
                "numbers, 0 disagreements. The four collection extents 585/55/10/1225 are "
                "agreed by every witness, while the extent of the grouping name "
                "'Purvarcika' is itself disputed (585 or 650), which is why the key names "
                "the four sub-collections and not the two top-level groupings."
            ),
            externally_frozen_before_change=False,
            downstream_impact=(
                "Every Samaveda canonical key, URN and UUID changes. Nothing downstream "
                "consumed them: identity_status was RESEARCH_REQUIRED and key_pattern was "
                "null throughout, no Samaveda release was ever published, and the only "
                "materialized rows are in a gitignored pilot build that is regenerated "
                "from pinned snapshots. No other work is affected."
            ),
            recorded_by_run=RUN,
        )
    )

    # 2. The spurious passage. Retired, and now unrepresentable rather than merely unused.
    migrations.append(
        ReferentMigration(
            migration_class=MigrationClass.PASSAGE_REMOVED_AS_SPURIOUS.value,
            old_canonical_key=PHANTOM_KEY,
            old_source_locator="GRETIL-SV 4.4.2.1.13",
            work_id=WORK_ID,
            reason=(
                "This key identified a verse that does not exist. Dasati (4,4,2,1) prints "
                "twelve verse numbers, 1116..1127, but the rejected witness's pada labels "
                "'12a' and '13c' are the two padas of ONE verse, so thirteen addresses "
                "were minted for twelve verses and printed verse 1127 was split across two "
                "keys."
            ),
            evidence=(
                "The selected witness prints exactly twelve verses in the corresponding "
                "dasati and the repaired build mints twelve keys there, so the thirteenth "
                "is confirmed spurious by an independent witness rather than only by "
                "internal arithmetic. The defect was invisible to the old build because "
                "the two pada labels landed in different verse buckets, so no duplicate "
                "label fired, and the corpus-wide shortage cancelled the local surplus in "
                "the total."
            ),
            externally_frozen_before_change=False,
            downstream_impact=(
                "None. The key was never materialized in any build output; it was minted "
                "only when the full rejected corpus was parsed. It is now unrepresentable: "
                "no dasati-local index above the printed verse count can be produced, "
                "because the index is derived from the printed running-number arithmetic "
                "and fails closed when that arithmetic does not close."
            ),
            recorded_by_run=RUN,
        )
    )

    # 3. Per-key rows for everything the pilot actually materialized.
    materialized: list[dict[str, object]] = []
    if PILOT_PASSAGES.exists():
        materialized = [
            json.loads(line)
            for line in PILOT_PASSAGES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    for record in materialized:
        old_key = str(record["canonical_key"])
        is_mantra = record.get("entity_type") == "MANTRA"
        mapped = new_mantra(old_key) if is_mantra else new_container(old_key)
        welded = WELDED_KEYS.get(old_key)
        migrations.append(
            ReferentMigration(
                migration_class=(
                    MigrationClass.REFERENT_CORRECTED.value
                    if welded
                    else MigrationClass.KEY_REASSIGNED_BEFORE_FREEZE.value
                ),
                old_canonical_key=old_key,
                old_canonical_urn=str(record.get("canonical_urn")),
                old_entity_id=str(record.get("entity_id")),
                old_source_locator=str(record.get("canonical_citation", "")),
                new_canonical_key=mapped[0] if mapped else None,
                new_canonical_urn=mapped[1] if mapped else None,
                new_entity_id=mapped[2] if mapped else None,
                work_id=WORK_ID,
                reason=(
                    "The key held a concatenative weld of printed verses "
                    f"{welded['markers']}; the repaired key denotes a single verse."
                    if welded
                    else "Key shape change only; the address denotes the same verse."
                ),
                evidence=(
                    welded["evidence"]
                    if welded
                    else "The old and new addresses agree on collection, prapathaka, "
                    "ardha and dasati under the recorded arcika-to-collection mapping; "
                    "only the spelling of the key changed."
                ),
                externally_frozen_before_change=False,
                downstream_impact=(
                    "Referent narrowed: text previously reachable under this key is now "
                    "reachable under sibling keys. Any consumer holding the old key held a "
                    "composite of several verses."
                    if welded
                    else "Key string, URN and UUID change; the textual referent does not."
                ),
                recorded_by_run=RUN,
            )
        )

    # 4. The welded keys that the pilot sample never materialized, so the ledger records
    #    the whole defect family rather than only the part that happened to be sampled.
    for old_key, detail in WELDED_KEYS.items():
        if any(row.old_canonical_key == old_key for row in migrations):
            continue
        mapped = new_mantra(old_key)
        migrations.append(
            ReferentMigration(
                migration_class=MigrationClass.REFERENT_CORRECTED.value,
                old_canonical_key=old_key,
                new_canonical_key=mapped[0] if mapped else None,
                new_canonical_urn=mapped[1] if mapped else None,
                new_entity_id=mapped[2] if mapped else None,
                work_id=WORK_ID,
                reason=(
                    "The key held a concatenative weld of printed verses "
                    f"{detail['markers']}; the repaired key denotes a single verse."
                ),
                evidence=detail["evidence"],
                externally_frozen_before_change=False,
                downstream_impact="Never materialized in a build output.",
                recorded_by_run=RUN,
            )
        )

    write_jsonl(OUT_PATH, migrations)
    by_class: dict[str, int] = {}
    for row in migrations:
        by_class[row.migration_class] = by_class.get(row.migration_class, 0) + 1
    print(json.dumps({"total": len(migrations), "by_class": by_class}, indent=2))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
