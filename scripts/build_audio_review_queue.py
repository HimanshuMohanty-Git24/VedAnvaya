#!/usr/bin/env python3
"""Build data/staging/audio_review_queue.jsonl -- owner decision E.

This environment cannot audition audio. So rather than pretend the listening gate passed,
this emits every item that requires an audible ear, with everything a reviewer needs to
judge it without going back to the pipeline: both candidate texts where a confusion is
possible, the media URL, the duration, and what specifically to listen for.

Every row is NEEDS_AUDIBLE_REVIEW. Nothing here is reviewed.

Two rules the queue design follows, both from earlier failures in this project:

A reviewer must never be shown only the mapping under test. A listening sheet here once
had a decisive row quoting what a *broken* mapping would play, so the reviewer confirmed
the defect. Where a plausible confusion exists -- an adjacent verse, a rival recension --
the row carries both candidates, unlabelled in `blind_candidates`, and the answer is not in
the row a reviewer reads.

Automated text comparison is not listening review, and metadata inspection is not
listening review. `prior_automated_checks` records what was already machine-verified
precisely so the reviewer knows what is *not* yet established: that the audio sounds like
the verse.
"""

from __future__ import annotations

import json
import os
import pathlib
import random
from hashlib import sha256
from typing import Any

from neo4j import GraphDatabase

STAGING = pathlib.Path("data/staging")
OUT = STAGING / "audio_review_queue.jsonl"
URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

SPAN_PREFIXES = tuple(f"VG:RV:SAK:M01:S0{n}:" for n in (65, 66, 67, 68, 69, 70))


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def sanskrit_for(session: Any, keys: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for start in range(0, len(keys), 1000):
        batch = keys[start : start + 1000]
        for record in session.run(
            """
            UNWIND $keys AS k
            MATCH (m:Mantra {canonical_key:k})-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE t.text_role IN ['PRIMARY_TEXT','EXTRACTED_FROM_CONTAINER']
            RETURN k AS key, t.text_nfc AS text
            """,
            keys=batch,
        ):
            out.setdefault(record["key"], record["text"])
    return out


def neighbour_key(key: str) -> str | None:
    """The next verse in the same hymn -- the commonest wrong answer for an audio mapping."""
    parts = key.split(":")
    try:
        n = int(parts[-1][1:])
    except (ValueError, IndexError):
        return None
    return ":".join([*parts[:-1], f"V{n + 1:03d}"])


def main() -> int:
    rows: list[dict[str, Any]] = []
    rng = random.Random(20260915)

    strata = [
        ("audio_rv", "RV_RECOVERED_150", "Rigvedic verses recovered in Wave 1", 4),
        ("audio_yv", "YV_RECOVERED", "Yajurvedic verses recovered by the comparator fix", 6),
        (
            "audio_av",
            "AV_COORDINATE_REMAPPED",
            "Atharvavedic verses recovered by the sukta-division fix",
            7,
        ),
        (
            "samaveda_music",
            "SV_CONTAINER_SCOPE",
            "Samavedic container-scope audio, never verse scope",
            5,
        ),
    ]

    staged: dict[str, list[dict[str, Any]]] = {}
    for domain, _, _, _ in strata:
        picked = []
        for r in read_jsonl(STAGING / domain / "rows.jsonl"):
            payload = r.get("payload") or {}
            if payload.get("audio_type") or payload.get("media_url"):
                picked.append(r)
                continue
            # The Samavedic container-scope rows nest their media under `performances`,
            # one row per arcika container with a list of gana performances touching it.
            # Flattened here so each performance is separately auditionable -- a reviewer
            # cannot judge "one of three recordings" as a single item.
            for performance in payload.get("performances") or []:
                flat = dict(r)
                merged = {k: v for k, v in payload.items() if k != "performances"}
                merged.update(performance)
                merged.setdefault("scope_type", payload.get("scope_type"))
                # Field aliasing so every queued row is auditionable by the same reader.
                # Commons gives a file *page*, not a direct media URL; that is what a
                # reviewer needs anyway, since the page carries the licence and credit.
                merged.setdefault("media_url", performance.get("source_url"))
                merged.setdefault(
                    "duration_seconds",
                    performance.get("duration_seconds_measured_from_container"),
                )
                merged.setdefault("performer", performance.get("performer_credited"))
                merged.setdefault("source_name", "Wikimedia Commons")
                flat["payload"] = merged
                picked.append(flat)
        staged[domain] = picked

    all_keys = sorted({r["canonical_key"] for rs in staged.values() for r in rs})

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            # The span's existing catalogue audio: clean on every machine check, queued
            # because decision E asks for 100% of the affected span.
            span_rows = list(
                session.run(
                    """
                    MATCH (m:Mantra {veda:'RV'})-[:HAS_TEXT_VERSION]->(t:TextVersion)
                    WHERE t.text_role = 'PRIMARY_TEXT'
                      AND any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
                    RETURN m.canonical_key AS key, m.canonical_citation AS cite, t.text_nfc AS text
                    ORDER BY key
                    """,
                    prefixes=list(SPAN_PREFIXES),
                )
            )
            span_keys = [r["key"] for r in span_rows]
            sanskrit = sanskrit_for(
                session, all_keys + span_keys + [k for key in all_keys if (k := neighbour_key(key))]
            )
    finally:
        driver.close()

    catalogue = {}
    catalogue_path = pathlib.Path("data/product/audio_catalog.jsonl")
    if catalogue_path.exists():
        for line in catalogue_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if (rec.get("scope_key") or "").startswith(SPAN_PREFIXES):
                catalogue[rec["scope_key"]] = rec

    # --- stratum 1: the affected span's existing audio -------------------------------
    for record in span_rows:
        key = record["key"]
        cat = catalogue.get(key, {})
        rows.append(
            {
                "review_id": f"REV-SPAN-{key}",
                "stratum": "RV_1_65_TO_1_70_AFFECTED_SPAN",
                "review_priority": 1,
                "canonical_key": key,
                "citation": record["cite"],
                "canonical_sanskrit": record["text"],
                "media_url": cat.get("media_url"),
                "duration_seconds": cat.get("duration_seconds"),
                "source_name": cat.get("source_name"),
                "performer": cat.get("performer"),
                "start_seconds": cat.get("start_seconds"),
                "end_seconds": cat.get("end_seconds"),
                "is_segmented": bool(cat.get("start_seconds")),
                "prior_automated_checks": {
                    "mapping_confidence": cat.get("mapping_confidence"),
                    "text_verified": cat.get("text_verified"),
                    "note": (
                        "Machine-verified EXACT and text_verified. NOT audibly verified. "
                        "The defect found in this span is in the translation layer, not "
                        "this one; these rows are queued because decision E requires 100% "
                        "of the affected span."
                    ),
                },
                "listen_for": (
                    "Does the recitation match the Sanskrit shown, verse for verse? These "
                    "hymns are where an edition merges verse pairs, so the specific risk is "
                    "a recording of the verse pair rather than of this verse alone."
                ),
                "blind_candidates": None,
                "review_status": "NEEDS_AUDIBLE_REVIEW",
                "reviewer": None,
                "reviewed_at": None,
                "verdict": None,
                "reviewer_notes": None,
            }
        )

    # --- strata 2-5: Wave 1's staged audio -------------------------------------------
    for domain, stratum, description, priority in strata:
        for r in staged[domain]:
            key = r["canonical_key"]
            payload = r.get("payload") or {}
            neighbour = neighbour_key(key)
            blind = None
            if neighbour and neighbour in sanskrit and sanskrit.get(key):
                pair = [
                    {"label": "A", "sanskrit": sanskrit[key]},
                    {"label": "B", "sanskrit": sanskrit[neighbour]},
                ]
                rng.shuffle(pair)
                blind = {
                    "instruction": (
                        "One of these is the verse this recording is mapped to and one is "
                        "its neighbour. Say which you hear, without consulting the key."
                    ),
                    "candidates": pair,
                }
            rows.append(
                {
                    "review_id": f"REV-{stratum}-{key}",
                    "stratum": stratum,
                    "stratum_description": description,
                    "review_priority": priority,
                    "canonical_key": key,
                    "citation": payload.get("scope_key") or key,
                    "canonical_sanskrit": sanskrit.get(key),
                    "media_url": payload.get("media_url"),
                    "duration_seconds": payload.get("duration_seconds"),
                    "source_name": payload.get("source_name"),
                    "performer": payload.get("performer"),
                    "start_seconds": payload.get("start_seconds"),
                    "end_seconds": payload.get("end_seconds"),
                    "is_segmented": payload.get("start_seconds") is not None,
                    "scope_type": payload.get("scope_type"),
                    "recension": payload.get("recension"),
                    "mapping_confidence": r.get("mapping_confidence"),
                    "prior_automated_checks": {
                        "mapping_method": r.get("mapping_method"),
                        "recension_evidence": r.get("recension_evidence"),
                        "text_verified": payload.get("text_verified"),
                        "note": (
                            "Text and structural checks only. No one has heard this. "
                            "Automated text comparison is not listening review."
                        ),
                    },
                    "listen_for": (
                        "Is this the mapped verse, recited in the recension claimed, whole "
                        "and not truncated? If a start/end time is present, do the "
                        "boundaries fall at the verse edges?"
                    ),
                    "blind_candidates": blind,
                    "review_status": "NEEDS_AUDIBLE_REVIEW",
                    "reviewer": None,
                    "reviewed_at": None,
                    "verdict": None,
                    "reviewer_notes": None,
                }
            )

    rows.sort(key=lambda r: (r["review_priority"], r["canonical_key"]))
    OUT.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
        newline="\n",
    )

    import collections

    by_stratum = collections.Counter(r["stratum"] for r in rows)
    segmented = sum(1 for r in rows if r["is_segmented"])
    blinded = sum(1 for r in rows if r["blind_candidates"])
    no_media = sum(1 for r in rows if not r["media_url"])

    print(f"queue: {len(rows)} rows -> {OUT}")
    print(f"sha256: {sha256(OUT.read_bytes()).hexdigest()[:16]}")
    for stratum, count in by_stratum.most_common():
        print(f"  {stratum:34} {count:>5}")
    print(f"\nsegmented (boundary review required): {segmented}")
    print(f"rows carrying a blind neighbour pair : {blinded}")
    print(f"rows with no media_url               : {no_media}")
    print(
        f"review_status NEEDS_AUDIBLE_REVIEW   : "
        f"{sum(1 for r in rows if r['review_status'] == 'NEEDS_AUDIBLE_REVIEW')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
