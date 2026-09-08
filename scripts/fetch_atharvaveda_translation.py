"""Stage Whitney & Lanman (1905) AVS translations, aligned by printed citation only.

Why this exists as a separate step
----------------------------------
Translations must be independent records aligned by the translation's *own printed numbers*,
never by sequence position (ADR-010).  Whitney's numbering is known to diverge from the
Saunaka Samhita numbering, so a zip() over two lists would have produced records that look
complete and are wrong.  This script therefore resolves every mantra through VedaWeb's
location **alias** index -- the aliases are the printed book.hymn.stanza labels -- and emits
nothing at all where the alias does not resolve.

Source
------
VedaWeb 2.0 (Tekst platform, University of Cologne) resource
``696f42266f50da42570ad040``, "Whitney & Lanman (1905)", plainText at level 2 (Stanza), of
text ``68b049424a624d3e1abc8188`` = "Atharvaveda Saunaka".

Rights, and the distinction that matters
----------------------------------------
The *underlying work* is Harvard Oriental Series vols VII-VIII, Cambridge MA 1905: published
before 1931 and therefore public domain in the United States (Lanman d. 1941).  English
Wikisource independently tags the same edition ``{{PD/US|1941}}``.

The *digital layer* declares ``"license": null`` on VedaWeb.  Unlike VedaWeb's AVS **Sanskrit**
resource -- which carries the TITUS clause "No parts of this document may be republished in
any form without prior permission by the copyright holder" verbatim in its description --
this translation resource carries **no** restrictive statement, only a citation request.
Both facts are recorded in the staged payload so that the rights authority can adjudicate
on evidence rather than on this script's opinion.

Every HTTP GET here has a stable URL and goes through ``PoliteFetcher``, so each response is
an immutable hashed snapshot under ``data/raw/vedaweb_avs/`` and a rerun reuses the cache.
The two-step ``/resources/{id}/export`` flow was deliberately NOT used: its download URL
contains an ephemeral ``pickupKey`` and would not be reproducible.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import orjson

from vedagraph.config import Settings
from vedagraph.ingest.fetcher import PoliteFetcher

#: Registered source id. The Whitney layer is another ARTIFACT of VEDAWEB, not a new
#: source: VedaWeb's AVS Sanskrit resource carries the TITUS no-republication clause while
#: this translation resource returns a null licence. Same host, opposite verdicts, so rights
#: belong at the artifact level and a "VEDAWEB_AVS" source-level value could not be correct.
SOURCE_ID = "VEDAWEB"
#: Local raw-snapshot namespace, deliberately separate from the registered source id so
#: these snapshots do not mix into the Rigveda's data/raw/vedaweb/.
SNAPSHOT_SOURCE_ID = "VEDAWEB_AVS"
SOURCE_ARTIFACT_ID = "VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2"
API = "https://vedaweb.uni-koeln.de/api"
TEXT_ID = "68b049424a624d3e1abc8188"
TEXT_SLUG = "avs"
WHITNEY_RESOURCE_ID = "696f42266f50da42570ad040"
SANSKRIT_RESOURCE_ID = "696f331f6f50da42570ad028"

TRANSLATOR = "William Dwight Whitney (revised and edited by Charles Rockwell Lanman)"
WORK_EDITION = (
    "Atharva-Veda Samhita, translated with a critical and exegetical commentary. "
    "Harvard Oriental Series 7-8. Cambridge, MA: Harvard University Press, 1905"
)
YEAR = 1905

RIGHTS_EVIDENCE = {
    "underlying_work_status": "PUBLIC_DOMAIN",
    "underlying_work_basis": (
        "published 1905, before 1931, therefore public domain in the United States; "
        "longest-living author Charles Rockwell Lanman died 1941"
    ),
    "corroboration": (
        "English Wikisource tags the same edition {{PD/US|1941}} at "
        "https://en.wikisource.org/wiki/Atharva-Veda_Samhita"
    ),
    "digital_layer_declared_license": None,
    "digital_layer_note": (
        'VedaWeb resource 696f42266f50da42570ad040 returns "license": null and '
        '"licenseUrl": null. It carries NO restrictive statement. This is materially '
        "different from VedaWeb's AVS Sanskrit resource 696f331f6f50da42570ad028, whose "
        'description reproduces verbatim: "Copyright TITUS Project, Frankfurt a/M, '
        "4.3.2015. No parts of this document may be republished in any form without prior "
        'permission by the copyright holder." That clause attaches to the Sanskrit text, '
        "not to this translation."
    ),
    "citation_required_verbatim": (
        "Whitney, William Dwight & Charles Rockwell Lanman. 1905. Atharva-Veda Samhita. "
        "Translated with a critical and exegetical commentary by William Dwight Whitney. "
        "Revised and brought nearer to completion and edited by Charles Rockwell Lanman. "
        "Cambridge, MA: Harvard University Press. Curated and hosted by VedaWeb - Online "
        "Research Platform for Old Indic texts. University of Cologne."
    ),
    "platform_site_notice_verbatim": (
        "Individual resources provide their own citation guidelines, which can be found in "
        "the resource information. Please use these for citing specific data."
    ),
}

#: Kept in step with scripts/build_atharvaveda_pilot.py SAMPLE.
SAMPLE_SUKTAS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (4, 1),
    (6, 1),
    (7, 6),
    (8, 5),
    (13, 4),
    (15, 2),
    (16, 1),
    (19, 1),
    (20, 96),
    (20, 127),
)


def _load(path: Path) -> Any:
    return orjson.loads(path.read_bytes())


async def stage(settings: Settings, out_path: Path) -> dict[str, Any]:
    fetcher = PoliteFetcher(settings)

    # One stable GET for the whole translation layer, keyed by opaque location id.
    contents_url = f"{API}/contents?res={WHITNEY_RESOURCE_ID}&limit=6000"
    contents_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, contents_url)
    contents = _load(contents_snap.content_path)
    by_location = {row["locationId"]: row for row in contents if row.get("text")}

    snapshots = [contents_snap.metadata.snapshot_id]
    verses: list[dict[str, Any]] = []
    unresolved: list[str] = []
    hymn_alias_misses: list[str] = []

    for kanda, sukta in SAMPLE_SUKTAS:
        # Resolve the hymn by its PRINTED label, not by position.
        hymn_url = f"{API}/locations?textSlug={TEXT_SLUG}&alias={kanda}.{sukta}&fullLabels=true"
        hymn_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, hymn_url)
        snapshots.append(hymn_snap.metadata.snapshot_id)
        hymns = _load(hymn_snap.content_path)
        hymn = next((item for item in hymns if item.get("level") == 1), None)
        if hymn is None:
            hymn_alias_misses.append(f"{kanda}.{sukta}")
            continue

        children_url = f"{API}/locations?parentId={hymn['id']}&limit=100"
        children_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, children_url)
        snapshots.append(children_snap.metadata.snapshot_id)
        children = _load(children_snap.content_path)

        for child in children:
            label = str(child.get("label", ""))
            if not label.isdigit():
                # A non-numeric stanza label cannot be mapped onto the integer mantra slot
                # of the canonical key, so it is reported rather than coerced.
                unresolved.append(f"{kanda}.{sukta}.{label!r} (non-numeric label)")
                continue
            mantra = int(label)
            row = by_location.get(child["id"])
            if row is None:
                # Whitney does not translate every stanza (Book 20 is untranslated).
                # An absent translation yields no record. It is never back-filled from a
                # neighbouring verse.
                continue
            verses.append(
                {
                    "kanda": kanda,
                    "sukta": sukta,
                    "mantra": mantra,
                    "text": row["text"],
                    "language": "en",
                    "translator": TRANSLATOR,
                    "work_edition": WORK_EDITION,
                    "year": YEAR,
                    "source_id": SOURCE_ID,
                    "source_artifact_id": SOURCE_ARTIFACT_ID,
                    "rights_status": "PUBLIC_DOMAIN",
                    # The alias IS the printed citation, so the alignment is exact by
                    # construction rather than by assumption.
                    "alignment": "EXACT_MANTRA_ALIGNMENT",
                    "source_alias": next(
                        (
                            alias
                            for alias in child.get("aliases", [])
                            if alias == f"{kanda}.{sukta}.{mantra}"
                        ),
                        f"{kanda}.{sukta}.{mantra}",
                    ),
                    "page_title": f"AVS {kanda}.{sukta}.{mantra} (Whitney & Lanman 1905)",
                    "page_url": f"https://vedaweb.uni-koeln.de/{TEXT_SLUG}/browse/{kanda}.{sukta}.{mantra}",
                    "vedaweb_location_id": child["id"],
                }
            )

    payload = {
        "stage_version": "atharvaveda-translation-stage-v1",
        "work_id": "VG:WORK:AV:SAU",
        "source_id": SOURCE_ID,
        "snapshot_source_id": SNAPSHOT_SOURCE_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "vedaweb_text_id": TEXT_ID,
        "vedaweb_resource_id": WHITNEY_RESOURCE_ID,
        "alignment_method": (
            "resolved through VedaWeb location aliases, which are the printed "
            "book.hymn.stanza labels; NEVER by sequence position"
        ),
        "rights_evidence": RIGHTS_EVIDENCE,
        "translation_layer_total_contents": len(contents),
        "sample_suktas": [f"{k}.{s}" for k, s in SAMPLE_SUKTAS],
        "hymn_alias_misses": hymn_alias_misses,
        "unresolved_stanza_labels": unresolved,
        "snapshot_ids": sorted(set(snapshots)),
        "verses": sorted(verses, key=lambda item: (item["kanda"], item["sukta"], item["mantra"])),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    return {
        "out": str(out_path),
        "translation_layer_total_contents": len(contents),
        "staged_verses": len(verses),
        "hymn_alias_misses": hymn_alias_misses,
        "unresolved_stanza_labels": unresolved,
        "snapshots": len(set(snapshots)),
    }


# ---------------------------------------------------------------------------------------
# Full-corpus staging (working private corpus)
# ---------------------------------------------------------------------------------------
#
# The sample path above resolves ONE hymn alias per sukta, which costs two requests per
# sukta and does not scale to 731 suktas. The full path walks the location tree instead:
# 20 kanda-alias lookups, 20 kanda-children lookups, then one children lookup per sukta.
# It is still alias-driven -- every stanza is attached by the aliases VedaWeb prints for
# it, never by list position -- so ADR-010 holds exactly as it does for the sample.
#
# The locations endpoint caps `limit` at 100 and offers NO pagination -- limit=200 and
# beyond return HTTP 422, and pg/page/skip/offset/from are all ignored -- so a kanda with
# more than 100 suktas cannot be listed in one call. Kandas 6 (142), 7 (118) and 20 (143)
# are exactly that case. Rather than accept a silently truncated page, this walk takes the
# set of suktas that the PRIMARY Sanskrit artifact actually contains and resolves any sukta
# missing from a truncated kanda listing through its own printed alias. Stanzas are safe at
# limit=100: the longest sukta in the primary artifact has 89.

FULL_STAGE_VERSION = "atharvaveda-translation-stage-full-v1"


def _alias_triple(entry: dict[str, Any]) -> tuple[int, int, int] | None:
    """Read (kanda, sukta, mantra) out of a stanza location's own printed aliases.

    Returns None when no alias is a plain dotted integer triple. A stanza whose printed
    label is not an integer has no integer mantra slot in the canonical key, so it is
    reported by the caller rather than coerced into one.
    """
    candidates = [str(entry.get("full") or "")] + [str(a) for a in entry.get("aliases", [])]
    for alias in candidates:
        parts = alias.split(".")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            return int(parts[0]), int(parts[1]), int(parts[2])
    return None


async def stage_full(
    settings: Settings,
    out_path: Path,
    *,
    required: dict[int, set[int]] | None = None,
) -> dict[str, Any]:
    """Stage the whole Whitney layer.

    ``required`` maps kanda -> sukta numbers that the primary Sanskrit artifact contains.
    When given it is the authority on what must be resolved; when absent the walk trusts
    VedaWeb's own kanda listings, which truncate at 100 children.
    """
    fetcher = PoliteFetcher(settings)

    contents_url = f"{API}/contents?res={WHITNEY_RESOURCE_ID}&limit=6000"
    contents_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, contents_url)
    contents = _load(contents_snap.content_path)
    by_location = {row["locationId"]: row for row in contents if row.get("text")}

    snapshots = [contents_snap.metadata.snapshot_id]
    verses: list[dict[str, Any]] = []
    unresolved: list[str] = []
    kanda_alias_misses: list[str] = []
    sukta_alias_misses: list[str] = []
    truncated_stanza_pages: list[str] = []
    suktas_seen: list[str] = []

    for kanda in range(1, 21):
        kanda_url = f"{API}/locations?textSlug={TEXT_SLUG}&alias={kanda}&fullLabels=true"
        kanda_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, kanda_url)
        snapshots.append(kanda_snap.metadata.snapshot_id)
        entries = _load(kanda_snap.content_path)
        node = next((item for item in entries if item.get("level") == 0), None)
        if node is None:
            kanda_alias_misses.append(str(kanda))
            continue

        suktas_url = f"{API}/locations?parentId={node['id']}&limit=100"
        suktas_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, suktas_url)
        snapshots.append(suktas_snap.metadata.snapshot_id)
        listed: dict[int, dict[str, Any]] = {}
        for sukta_node in _load(suktas_snap.content_path):
            sukta_label = str(sukta_node.get("label", ""))
            if not sukta_label.isdigit():
                unresolved.append(f"{kanda}.{sukta_label!r} (non-numeric sukta label)")
                continue
            listed[int(sukta_label)] = sukta_node

        # The primary artifact decides which suktas must be resolved, so a truncated page
        # shows up as extra alias lookups rather than as missing translations.
        wanted = sorted(required.get(kanda, set(listed))) if required else sorted(listed)
        for sukta in wanted:
            sukta_node = listed.get(sukta)
            if sukta_node is None:
                alias_url = (
                    f"{API}/locations?textSlug={TEXT_SLUG}&alias={kanda}.{sukta}&fullLabels=true"
                )
                alias_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, alias_url)
                snapshots.append(alias_snap.metadata.snapshot_id)
                sukta_node = next(
                    (item for item in _load(alias_snap.content_path) if item.get("level") == 1),
                    None,
                )
                if sukta_node is None:
                    sukta_alias_misses.append(f"{kanda}.{sukta}")
                    continue
            suktas_seen.append(f"{kanda}.{sukta}")

            children_url = f"{API}/locations?parentId={sukta_node['id']}&limit=100"
            children_snap = await fetcher.fetch(SNAPSHOT_SOURCE_ID, children_url)
            snapshots.append(children_snap.metadata.snapshot_id)
            children = _load(children_snap.content_path)
            if len(children) == 100:
                # 100 is the hard page size, so an exactly-full page may be truncated.
                truncated_stanza_pages.append(f"{kanda}.{sukta}")

            for child in children:
                triple = _alias_triple(child)
                if triple is None:
                    unresolved.append(
                        f"{kanda}.{sukta}.{child.get('label')!r} (no integer alias triple)"
                    )
                    continue
                alias_kanda, alias_sukta, mantra = triple
                if (alias_kanda, alias_sukta) != (kanda, sukta):
                    # The stanza's own printed citation disagrees with the parent it hangs
                    # under. Reported, never silently re-parented.
                    unresolved.append(
                        f"{kanda}.{sukta}.{child.get('label')!r} "
                        f"(alias says {alias_kanda}.{alias_sukta}.{mantra})"
                    )
                    continue
                row = by_location.get(child["id"])
                if row is None:
                    # Whitney does not translate every stanza. An absent translation yields
                    # no record; it is never back-filled from a neighbouring verse.
                    continue
                verses.append(
                    {
                        "kanda": kanda,
                        "sukta": sukta,
                        "mantra": mantra,
                        "text": row["text"],
                        "language": "en",
                        "translator": TRANSLATOR,
                        "work_edition": WORK_EDITION,
                        "year": YEAR,
                        "source_id": SOURCE_ID,
                        "source_artifact_id": SOURCE_ARTIFACT_ID,
                        "rights_status": "PUBLIC_DOMAIN",
                        "alignment": "EXACT_MANTRA_ALIGNMENT",
                        "source_alias": f"{kanda}.{sukta}.{mantra}",
                        "page_title": f"AVS {kanda}.{sukta}.{mantra} (Whitney & Lanman 1905)",
                        "page_url": (
                            f"https://vedaweb.uni-koeln.de/{TEXT_SLUG}/browse/"
                            f"{kanda}.{sukta}.{mantra}"
                        ),
                        "vedaweb_location_id": child["id"],
                    }
                )

    payload = {
        "stage_version": FULL_STAGE_VERSION,
        "work_id": "VG:WORK:AV:SAU",
        "source_id": SOURCE_ID,
        "snapshot_source_id": SNAPSHOT_SOURCE_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "vedaweb_text_id": TEXT_ID,
        "vedaweb_resource_id": WHITNEY_RESOURCE_ID,
        "alignment_method": (
            "walked the VedaWeb location tree kanda -> sukta -> stanza and attached every "
            "stanza by its OWN printed alias triple; NEVER by sequence position"
        ),
        "rights_evidence": RIGHTS_EVIDENCE,
        "translation_layer_total_contents": len(contents),
        "scope": "FULL_CORPUS",
        "suktas_walked": len(suktas_seen),
        "kanda_alias_misses": kanda_alias_misses,
        "sukta_alias_misses": sukta_alias_misses,
        "truncated_stanza_pages": truncated_stanza_pages,
        "unresolved_stanza_labels": unresolved,
        "snapshot_ids": sorted(set(snapshots)),
        "verses": sorted(verses, key=lambda item: (item["kanda"], item["sukta"], item["mantra"])),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    return {
        "out": str(out_path),
        "scope": "FULL_CORPUS",
        "translation_layer_total_contents": len(contents),
        "suktas_walked": len(suktas_seen),
        "staged_verses": len(verses),
        "kanda_alias_misses": kanda_alias_misses,
        "sukta_alias_misses": sukta_alias_misses,
        "truncated_stanza_pages": truncated_stanza_pages,
        "unresolved_stanza_labels": len(unresolved),
        "snapshots": len(set(snapshots)),
    }


def _suktas_in_primary_artifact() -> dict[int, set[int]]:
    """kanda -> sukta numbers present in the cached GRETIL AVS snapshots.

    Read from the snapshots the build itself reads, so translation coverage is measured
    against this corpus's own structure rather than against VedaWeb's navigation tree.
    Either GRETIL variant answers this question identically -- the accented and unaccented
    files carry the same 731 locators -- so any parseable snapshot in the namespace is
    accepted, and ``assert_saunaka_recension`` inside ``parse_units`` still refuses a file
    that is not the Saunaka Atharvaveda.
    """
    from vedagraph.ingest.adapters.atharvaveda_gretil import (
        SNAPSHOT_SOURCE_ID as GRETIL_SNAPSHOT_SOURCE_ID,
    )
    from vedagraph.ingest.adapters.atharvaveda_gretil import GretilAVSAdapter

    # The GRETIL namespace, NOT this module's VEDAWEB_AVS namespace: the structure comes
    # from the primary Sanskrit artifact, the translations come from VedaWeb.
    root = Settings().data_dir / "raw" / GRETIL_SNAPSHOT_SOURCE_ID.lower()
    adapter = GretilAVSAdapter(variant="ACCENTED")
    out: dict[int, set[int]] = {}
    for path in sorted(root.rglob("*.htm")):
        for unit in adapter.parse_units(path):
            out.setdefault(unit.kanda, set()).add(unit.sukta)
    if not out:
        raise FileNotFoundError(f"no parseable GRETIL AVS snapshot under {root}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path("data/staged/atharvaveda_translation_stage.json")
    )
    parser.add_argument(
        "--scope",
        choices=("sample", "full"),
        default="sample",
        help="sample = the 11 pilot suktas; full = all 20 kandas via the location tree",
    )
    args = parser.parse_args()
    if args.scope == "full":
        summary = asyncio.run(
            stage_full(Settings(), args.out, required=_suktas_in_primary_artifact())
        )
    else:
        summary = asyncio.run(stage(Settings(), args.out))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
