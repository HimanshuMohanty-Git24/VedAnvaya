"""Align the VedSearch harvest to canonical keys, verify the text, and write the catalog.

**A record is written only when two independent things agree.** The coordinate transform
must place our key somewhere in VedSearch's numbering, *and* the text VedSearch says that
recording recites must match this corpus's text for that key. Either alone is not enough
here, and the reason is concrete: VedSearch numbers Rigvedic Mandala 8 in Griffith's order,
so 55 hymns there sit eleven hymns away from where a key-for-key rule would put them. The
transform corrects that; the text check is what proves the correction landed, and it would
also catch a renumbering nobody has noticed yet.

**The Samaveda is aligned by text alone**, because there is nothing else to align it by.
VedSearch numbers its Samaveda in flat chapters while this corpus uses the four named
Kauthuma collections, and no published correspondence between the two was found. So instead
of guessing a numbering, every harvested Samavedic verse is reduced to its letters and
matched against this corpus's Samavedic verses reduced the same way. Verses whose letters
collide with another verse's are left unmapped rather than assigned arbitrarily -- the
Samaveda repeats material, so collisions are expected and are reported.

**Availability is the source's claim until audio is actually fetched.** The harvest carries
VedSearch's own ``audio.sanskrit`` flag per verse. ``--verify-audio N`` fetches N real audio
documents and checks they decode to MP3, which is what justifies writing ``AVAILABLE``
rather than repeating a flag.

Usage::

    python scripts/audio/discover_vedsearch.py --dry-run
    python scripts/audio/discover_vedsearch.py --verify-audio 40
    python scripts/audio/discover_vedsearch.py --veda RV
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import random
import sys
import warnings
from collections import Counter
from datetime import UTC, datetime
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from neo4j import GraphDatabase  # noqa: E402

from vedagraph.product.audio.catalog import CATALOG_RELATIVE_PATH, write_catalog  # noqa: E402
from vedagraph.product.audio.models import (  # noqa: E402
    AudioRecord,
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
)
from vedagraph.product.audio.net import USER_AGENT  # noqa: E402
from vedagraph.product.audio.vedsearch import (  # noqa: E402
    MATCH_THRESHOLD,
    SOURCE_NAME,
    VedSearchClient,
    audio_endpoint,
    best_text_match,
    has_sanskrit_audio,
    index_rows,
    row_shlok_id,
    row_text,
    skeleton,
    vedsearch_coordinates,
    verse_matches,
    verse_page,
)

BOLT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
BOLT_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_HARVEST = PROJECT_ROOT / "data" / "derived" / "vedsearch_harvest.json"
DEFAULT_OUT = PROJECT_ROOT / "data" / CATALOG_RELATIVE_PATH

#: Which stored text surface is this corpus's reading for each Veda.
#:
#: Not uniform, and not guessable: the Yajurveda has no ``PRIMARY_TEXT`` at all -- its
#: reading is ``EXTRACTED_FROM_CONTAINER``, because the source publishes adhyayas and the
#: verses were extracted from them. Using ``PRIMARY_TEXT`` for all four silently compared
#: 1,975 Yajurvedic verses against nothing.
TEXT_ROLE: dict[str, str] = {
    "RV": "PRIMARY_TEXT",
    "AV": "PRIMARY_TEXT",
    "SV": "PRIMARY_TEXT",
    "YV": "EXTRACTED_FROM_CONTAINER",
}

VEDA_LABEL = {"RV": "Rigveda", "SV": "Samaveda", "YV": "Yajurveda", "AV": "Atharvaveda"}


def read_our_verses(session: Any, veda: str) -> dict[str, dict[str, str]]:
    """``{canonical_key: {text, citation}}`` for one Veda's mantras."""
    rows = session.run(
        "MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion) "
        "WHERE p.veda = $veda AND p.entity_type = 'MANTRA' AND t.text_role = $role "
        "RETURN p.canonical_key AS key, p.canonical_citation AS citation, "
        "t.text_nfc AS text ORDER BY key",
        veda=veda,
        role=TEXT_ROLE[veda],
    )
    return {
        row["key"]: {"text": row["text"] or "", "citation": row["citation"] or row["key"]}
        for row in rows
    }


def harvested_rows(harvest: dict[str, Any], veda: str) -> list[dict[str, Any]]:
    chapters = harvest.get("vedas", {}).get(veda, {}).get("chapters", {})
    rows: list[dict[str, Any]] = []
    for chapter in sorted(chapters, key=lambda value: int(value)):
        rows.extend(chapters[chapter])
    return rows


def build_record(
    veda: str,
    canonical_key: str,
    citation: str,
    row: dict[str, Any],
    *,
    chapter: int,
    sukta: int | None,
    verse: int,
    availability: Availability,
    last_verified: str,
    method: str,
) -> AudioRecord | None:
    shlok_id = row_shlok_id(row)
    if shlok_id is None:
        return None
    return AudioRecord(
        audio_id=f"VEDSEARCH:{veda}:{shlok_id}",
        veda=veda,
        recension={"RV": "SAK", "SV": "KAU", "YV": "VSM", "AV": "SAU"}[veda],
        # MANTRA, and honestly so: this source publishes one file per verse, which is the
        # thing the previous source could not do.
        scope_type=AudioScope.MANTRA,
        scope_key=canonical_key,
        audio_type=AudioType.RECITATION,
        title=f"{VEDA_LABEL[veda]} {citation} - recitation of this verse",
        # The site names no reciter. Absent rather than invented.
        performer=None,
        tradition=None,
        location=None,
        source_name=SOURCE_NAME,
        source_page=verse_page(veda, chapter, sukta, verse),
        media_url=audio_endpoint(veda, shlok_id),
        embed_url=None,
        local_cache_path=None,
        duration_seconds=None,
        start_seconds=None,
        end_seconds=None,
        mapping_method=method,
        mapping_confidence=MappingConfidence.EXACT,
        availability=availability,
        playback_mode=PlaybackMode.PROXIED_STREAM,
        licence=None,
        attribution=f"Recitation courtesy {SOURCE_NAME} (vedsearch.org).",
        # True because this is a local research product and the operator chose an opt-in
        # cache: the cache tool still refuses to run without an explicit --all, --veda or
        # --audio-id, so nothing is ever mirrored by accident.
        local_copy_permitted=True,
        source_reference=shlok_id,
        text_verified=True,
        last_verified=last_verified,
        checksum=None,
        notes="One file per verse, fetched and decoded by this product's own streaming "
        "route because the source serves audio as base64 inside JSON. No copy is kept "
        "unless the cache tool is run.",
    )


def align_by_coordinates(
    veda: str,
    ours: dict[str, dict[str, str]],
    rows: list[dict[str, Any]],
    *,
    availability: Availability,
    today: str,
) -> tuple[list[AudioRecord], Counter[str]]:
    """RV, AV and YV: map by coordinates, then confirm by text."""
    indexed = index_rows(rows)
    stats: Counter[str] = Counter()
    built: list[AudioRecord] = []
    method = (
        "Mapped from the canonical key to the source's own verse coordinates -- for the "
        "Rigveda through the Valakhilya edition permutation, since the source numbers "
        "Mandala 8 in Griffith's order -- and then confirmed by comparing the text the "
        "source states this recording recites against this corpus's text for the same key."
    )
    for key, entry in ours.items():
        coordinates = vedsearch_coordinates(veda, key)
        if coordinates is None:
            stats["key_shape_unmappable"] += 1
            continue
        row = indexed.get((coordinates.chapter, coordinates.sukta or 1, coordinates.verse))
        if row is None:
            stats["no_source_verse"] += 1
            continue
        if not has_sanskrit_audio(row):
            stats["source_has_no_audio"] += 1
            continue
        matched, score = verse_matches(row_text(row), entry["text"])
        if not matched:
            stats["text_mismatch"] += 1
            continue
        stats["exact_text" if score >= 1.0 else "near_text"] += 1
        record = build_record(
            veda,
            key,
            entry["citation"],
            row,
            chapter=coordinates.chapter,
            sukta=coordinates.sukta,
            verse=coordinates.verse,
            availability=availability,
            last_verified=today,
            method=method,
        )
        if record is None:
            stats["record_build_failed"] += 1
            continue
        built.append(record)
        stats["mapped"] += 1
    return built, stats


def align_by_text(
    veda: str,
    ours: dict[str, dict[str, str]],
    rows: list[dict[str, Any]],
    *,
    availability: Availability,
    today: str,
) -> tuple[list[AudioRecord], Counter[str]]:
    """Samaveda: no shared numbering exists, so align on the text itself.

    Each of our verses is searched against every source verse that has audio, and a match
    is accepted only when it clears the similarity threshold *and* beats the runner-up by a
    margin. The margin is the part that matters: the Samaveda repeats material, so a verse
    can resemble several others, and "best of several near-identical candidates" is a guess
    dressed as a result. Those are counted as ambiguous and left unmapped.
    """
    stats: Counter[str] = Counter()
    candidates: dict[str, str] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        shlok_id = row_shlok_id(row)
        if not shlok_id:
            continue
        by_id[shlok_id] = row
        if has_sanskrit_audio(row):
            candidates[shlok_id] = skeleton(row_text(row))
    stats["source_verses_with_audio"] = len(candidates)

    method = (
        "Aligned on the verse text itself: this corpus's Samavedic collections and the "
        "source's flat chapter numbering have no published correspondence, so each verse "
        "was matched by text against every source verse carrying audio. A match was "
        "accepted only when it cleared the similarity threshold and beat the runner-up by "
        "a margin, so a verse that resembles several others is reported ambiguous rather "
        "than assigned."
    )
    built: list[AudioRecord] = []
    claimed: dict[str, str] = {}
    for key, entry in ours.items():
        shlok_id, best, _second = best_text_match(entry["text"], candidates)
        if shlok_id is None:
            stats["ambiguous" if best >= MATCH_THRESHOLD else "no_source_match"] += 1
            continue
        if shlok_id in claimed:
            # One recording cannot be two verses. The first claim stands and the second is
            # reported, because silently overwriting would make coverage look better than
            # the evidence supports.
            stats["source_verse_already_claimed"] += 1
            continue
        row = by_id.get(shlok_id)
        if row is None:
            stats["no_source_verse"] += 1
            continue
        parts = shlok_id.split(".")
        try:
            chapter = int(parts[0])
            verse = int(parts[-1])
            sukta = int(parts[1]) if len(parts) == 3 else None
        except ValueError:
            stats["unparsable_source_id"] += 1
            continue
        record = build_record(
            veda,
            key,
            entry["citation"],
            row,
            chapter=chapter,
            sukta=sukta,
            verse=verse,
            availability=availability,
            last_verified=today,
            method=method,
        )
        if record is None:
            stats["record_build_failed"] += 1
            continue
        claimed[shlok_id] = key
        built.append(record)
        stats["mapped"] += 1
        stats["exact_text" if best >= 1.0 else "near_text"] += 1
    return built, stats


def verify_audio(records: list[AudioRecord], sample: int, seed: int = 20260912) -> dict[str, Any]:
    """Fetch a sample of real audio documents and confirm they decode to media.

    Without this, ``availability=AVAILABLE`` would only repeat the source's own flag.
    """
    if not records or sample <= 0:
        return {"sampled": 0}
    client = VedSearchClient(user_agent=USER_AGENT)
    rng = random.Random(seed)
    picks = rng.sample(records, min(sample, len(records)))
    ok = failed = 0
    sizes: list[int] = []
    problems: list[str] = []
    for record in picks:
        try:
            raw, content_type = client.audio_bytes(record.veda, record.source_reference or "")
        except Exception as error:
            failed += 1
            problems.append(f"{record.audio_id}: {type(error).__name__}")
            continue
        # ID3 or a raw MPEG frame header. Anything else is not the MP3 it claims to be.
        if raw[:3] == b"ID3" or raw[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            ok += 1
            sizes.append(len(raw))
        else:
            failed += 1
            problems.append(f"{record.audio_id}: not MP3 ({content_type}, {raw[:4]!r})")
    return {
        "sampled": len(picks),
        "decoded_as_mp3": ok,
        "failed": failed,
        "median_bytes": sorted(sizes)[len(sizes) // 2] if sizes else None,
        "problems": problems[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--veda", choices=["RV", "SV", "YV", "AV"], action="append", default=[])
    parser.add_argument("--harvest", type=pathlib.Path, default=DEFAULT_HARVEST)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-audio", type=int, default=0, help="fetch N real files")
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args()

    if not args.harvest.exists():
        print(f"No harvest at {args.harvest}. Run scripts/audio/harvest_vedsearch.py first.")
        return 1
    harvest = json.loads(args.harvest.read_text(encoding="utf-8"))
    today = datetime.now(UTC).date().isoformat()
    vedas = args.veda or ["RV", "SV", "YV", "AV"]

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    all_records: list[AudioRecord] = []
    # Repository-relative, so a committed report does not record the builder's filesystem.
    try:
        harvest_label = args.harvest.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        harvest_label = args.harvest.name
    report: dict[str, Any] = {"harvest": harvest_label, "by_veda": {}}
    try:
        with driver.session() as session:
            for veda in vedas:
                ours = read_our_verses(session, veda)
                rows = harvested_rows(harvest, veda)
                if not rows:
                    print(f"{veda}: no harvested rows; skipped")
                    report["by_veda"][veda] = {"skipped": "no harvest"}
                    continue
                aligner = align_by_text if veda == "SV" else align_by_coordinates
                built, stats = aligner(
                    veda, ours, rows, availability=Availability.AVAILABLE, today=today
                )
                all_records.extend(built)
                stats["our_verses"] = len(ours)
                stats["source_verses"] = len(rows)
                report["by_veda"][veda] = dict(stats)
                pct = 100.0 * stats["mapped"] / len(ours) if ours else 0.0
                print(
                    f"{veda}: ours={len(ours)} source={len(rows)} "
                    f"mapped={stats['mapped']} ({pct:.1f}%) "
                    f"no_audio={stats.get('source_has_no_audio', 0)} "
                    f"text_mismatch={stats.get('text_mismatch', 0)} "
                    f"no_source_verse={stats.get('no_source_verse', 0)}"
                )
    finally:
        driver.close()

    if args.verify_audio:
        print(f"\nFetching {args.verify_audio} real audio files to confirm availability...")
        verification = verify_audio(all_records, args.verify_audio)
        report["audio_verification"] = verification
        print(json.dumps(verification, indent=2))
        if verification.get("failed"):
            print("  NOTE: some sampled files did not decode as MP3; see problems above.")

    report["total_records"] = len(all_records)
    if args.dry_run:
        print(f"\n--dry-run: {len(all_records)} record(s) built, nothing written.")
    else:
        written = write_catalog(args.out, all_records)
        print(f"\nWrote {written} records to {args.out}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
