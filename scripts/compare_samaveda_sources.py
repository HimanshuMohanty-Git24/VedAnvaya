"""Cross-witness STRUCTURAL validation of the Samaveda arcika coordinate system.

This compares ADDRESSES, not text. No Sanskrit from the rights-encumbered GRETIL artifact
is read, stored or printed here: the comparison uses its declared reference labels and its
printed running numbers only. That use is affirmatively granted -- the artifact carries
``verification_roles: [hierarchy, reference_system, edition_comparison]`` -- while its
``bulk_ingestion_status`` remains ``PROHIBITED_PENDING_RIGHTS_RESOLUTION``.

What it is for
--------------
The selected witness (Sanskrit Wikisource) declares the daśati partition of the
Uttarārcika with a numeral printed inside each ardha page. Some ardha pages omit some of
those numerals, which shifts every later daśati index on the page. A shifted index is a
moved referent under a well-formed key, so it must be measured rather than assumed away.

The join key is the printed running number, which is the one axis both witnesses state
directly. It is NOT injective on either side -- running number 1181 is printed twice in
both lineages -- so ambiguous values are reported and excluded from the agreement rate
instead of being silently first-won.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from vedagraph.identity import SamavedaCollection  # noqa: E402
from vedagraph.ingest.adapters.samaveda_gretil import SamavedaGRETILAdapter  # noqa: E402
from vedagraph.ingest.adapters.samaveda_wikisource import (  # noqa: E402
    SamavedaWikisourceAdapter,
    resolve_local_indices,
)

GRETIL_SNAPSHOT = (
    REPO
    / "data"
    / "raw"
    / "gretil"
    / "2026-09-07"
    / "91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456.xml"
)
WIKISOURCE_DIR = REPO / "data" / "raw" / "wikisource_sa"
OUT_PATH = REPO / "data" / "derived" / "samaveda_cross_witness_structure.json"

# How the rejected artifact's flat arcika ordinals map onto the named collections. This
# mapping is the whole content of the arity dispute: the Pandey lineage numbers the three
# Purvarcika sections as sibling top-level arcikas 1-3 and the Uttararcika as 4.
GRETIL_ARCIKA_TO_COLLECTION: dict[int, SamavedaCollection] = {
    1: SamavedaCollection.CHANDA,
    2: SamavedaCollection.ARANYA,
    3: SamavedaCollection.MAHANAMNYA,
    4: SamavedaCollection.UTTARA,
}


def gretil_by_running() -> tuple[dict[int, tuple], set[int]]:
    """Running number -> declared GRETIL coordinates, plus the non-injective values."""
    adapter = SamavedaGRETILAdapter()
    result = adapter.parse_structure(GRETIL_SNAPSHOT)
    holders: dict[int, list[tuple]] = defaultdict(list)
    for verse in result.verses:
        for running in verse.running_numbers:
            holders[running].append(verse.coordinates)
    ambiguous = {value for value, rows in holders.items() if len(set(rows)) > 1}
    return {value: rows[0] for value, rows in holders.items()}, ambiguous


def wikisource_by_running() -> tuple[dict[int, dict], set[int]]:
    adapter = SamavedaWikisourceAdapter()
    pages = []
    for meta in sorted(WIKISOURCE_DIR.rglob("*.metadata.json")):
        sha = meta.name.split(".")[0]
        body = meta.with_name(f"{sha}.php")
        if not body.exists():
            continue
        try:
            payload = json.loads(body.read_text(encoding="utf-8"))
        except ValueError:
            continue
        parse = payload.get("parse")
        if not parse:
            continue
        title = parse.get("title", "")
        if "/संहिता/पूर्वार्चिकः" not in title and "/संहिता/उत्तरार्चिकः" not in title:
            continue
        pages.append(adapter.parse_page(body, snapshot_sha256=sha))
    resolve_local_indices(pages)

    holders: dict[int, list[dict]] = defaultdict(list)
    for page in pages:
        for item in page.occurrences:
            if item.running_number is None:
                continue
            holders[item.running_number].append(
                {
                    "collection": item.collection.value,
                    "prapathaka": item.prapathaka,
                    "ardha": item.ardha,
                    "dasati": item.dasati,
                    "verse": item.local_index,
                    "page": item.page_title.rsplit("/", 1)[-1],
                }
            )
    ambiguous = {value for value, rows in holders.items() if len(rows) > 1}
    return {value: rows[0] for value, rows in holders.items()}, ambiguous


def main() -> None:
    gretil, gretil_ambiguous = gretil_by_running()
    wiki, wiki_ambiguous = wikisource_by_running()

    ambiguous = sorted(gretil_ambiguous | wiki_ambiguous)
    shared = sorted((set(gretil) & set(wiki)) - set(ambiguous))

    report: dict[str, object] = {
        "gretil_running_values": len(gretil),
        "wikisource_running_values": len(wiki),
        "shared_running_values": len(shared),
        "join_key_ambiguous_on_either_side": ambiguous,
        "only_in_gretil": sorted(set(gretil) - set(wiki)),
        "only_in_wikisource": sorted(set(wiki) - set(gretil)),
    }

    agree_collection = 0
    disagree: dict[str, list[dict]] = defaultdict(list)
    per_collection_levels: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for running in shared:
        g_arcika, g_prapathaka, g_ardha, g_dasati, g_verse = gretil[running]
        w = wiki[running]
        g_collection = GRETIL_ARCIKA_TO_COLLECTION.get(g_arcika)
        if g_collection is None:
            continue
        collection = w["collection"]
        stats = per_collection_levels[collection]
        stats["compared"] += 1

        if g_collection.value != collection:
            disagree["collection"].append(
                {"running": running, "gretil": g_collection.value, "wikisource": collection}
            )
            continue
        agree_collection += 1

        # Compare only the levels the collection actually declares. GRETIL writes a
        # literal 0 for a level it treats as absent, so those slots are not comparable.
        if collection == SamavedaCollection.CHANDA.value:
            pairs = (
                ("prapathaka", g_prapathaka, w["prapathaka"]),
                ("dasati", g_dasati, w["dasati"]),
            )
        elif collection == SamavedaCollection.ARANYA.value:
            pairs = (("dasati", g_dasati, w["dasati"]),)
        elif collection == SamavedaCollection.MAHANAMNYA.value:
            pairs = ()
        else:
            pairs = (
                ("prapathaka", g_prapathaka, w["prapathaka"]),
                ("ardha", g_ardha, w["ardha"]),
                ("dasati", g_dasati, w["dasati"]),
            )

        for level, gretil_value, wiki_value in pairs:
            if gretil_value == wiki_value:
                stats[f"{level}_agree"] += 1
            else:
                stats[f"{level}_disagree"] += 1
                disagree[level].append(
                    {
                        "running": running,
                        "gretil": gretil_value,
                        "wikisource": wiki_value,
                        "page": w["page"],
                    }
                )
        if g_verse == w["verse"]:
            stats["verse_agree"] += 1
        else:
            stats["verse_disagree"] += 1
            disagree["verse"].append(
                {
                    "running": running,
                    "gretil": g_verse,
                    "wikisource": w["verse"],
                    "page": w["page"],
                }
            )

    report["collection_agreement"] = {
        "agree": agree_collection,
        "disagree": len(disagree["collection"]),
    }
    report["per_collection_levels"] = {
        collection: dict(sorted(stats.items()))
        for collection, stats in sorted(per_collection_levels.items())
    }
    report["disagreement_counts"] = {level: len(rows) for level, rows in sorted(disagree.items())}
    # Pages whose dasati partition disagrees, which is the shifted-heading signature.
    pages_with_dasati_shift: dict[str, int] = defaultdict(int)
    for row in disagree["dasati"]:
        pages_with_dasati_shift[str(row["page"])] += 1
    report["pages_with_dasati_disagreement"] = dict(
        sorted(pages_with_dasati_shift.items(), key=lambda item: -item[1])
    )
    report["disagreement_samples"] = {level: rows[:12] for level, rows in sorted(disagree.items())}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    main()
