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

    # Each domain's sources.jsonl, keyed by source_id, so a queued row can name the source it
    # came from. Wave 4 finding: 804 of 1,021 rows carried source_name null, because this
    # builder read payload.source_name and the staged payloads do not have that field -- the
    # source is on the row as source_id and its name is in the domain's sources.jsonl. A
    # reviewer was given a media URL and left to infer whose recording it is, on the one
    # surface in this campaign whose entire purpose is a human judgement.
    #
    # The two files disagree about the field name (audio_yv writes source_name, audio_av
    # writes name), which is why both are read rather than one assumed.
    source_names: dict[str, str] = {}
    source_rights: dict[str, dict[str, Any]] = {}
    for domain, _, _, _ in strata:
        for source in read_jsonl(STAGING / domain / "sources.jsonl"):
            name = source.get("source_name") or source.get("name")
            if source.get("source_id") and name:
                source_names[str(source["source_id"])] = str(name)
            # The rights statement is spread over three field names, not one: `licence`
            # carries a declared licence where a source has one, and the researched finding
            # where it does not is under `rights_note` in the RV and AV files but
            # `licence_note` in the YV one. Reading only `licence` reports every source but
            # Vedavani as blank; reading only `rights_note` still leaves the 33 YV rows
            # blank. The value space is enumerated here rather than assumed.
            if source.get("source_id"):
                source_rights[str(source["source_id"])] = {
                    "licence": source.get("licence"),
                    "rights_note": source.get("rights_note") or source.get("licence_note"),
                }

    # The same records keyed by source NAME too, because the span rows below carry a name
    # from the product catalogue and no source_id at all.
    rights_by_name: dict[str, dict[str, Any]] = {
        source_names[sid]: rights
        for sid, rights in source_rights.items()
        if sid in source_names
    }

    def stated_licence(row: dict[str, Any], payload: dict[str, Any]) -> str:
        """The licence, or the researched reason there is none -- never a bare null.

        An empty licence cell reads as "unencumbered", and for the largest source here that
        is the opposite of the truth: VedSearch serves 819 of these rows under *"No licence
        statement."* A reviewer seeing a blank cannot tell a researched absence apart from a
        field nobody filled in, so the absence is typed into the row rather than left to a
        caveat somewhere else to carry.
        """
        explicit = payload.get("licence") or payload.get("license")
        if explicit:
            return str(explicit)
        source_id = row.get("source_id")
        rights = source_rights.get(str(source_id)) if source_id else None
        if rights is None:
            rights = rights_by_name.get(str(payload.get("source_name") or ""))
        if rights:
            if rights.get("licence"):
                return str(rights["licence"])
            if rights.get("rights_note"):
                return f"NO_DECLARED_LICENCE -- {rights['rights_note']}"
        return "NOT_RECORDED_IN_SOURCE_REGISTRY"

    def named_source(row: dict[str, Any], payload: dict[str, Any]) -> str | None:
        """The source's name, or its id, or its attribution -- never silently nothing.

        Falls back to the id rather than to null: an opaque identifier a reviewer can look up
        beats an empty field that reads as "no source recorded".
        """
        explicit = payload.get("source_name")
        if explicit:
            return str(explicit)
        source_id = row.get("source_id")
        if source_id:
            return source_names.get(str(source_id), str(source_id))
        attribution = payload.get("attribution")
        return str(attribution) if attribution else None

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
                # This stratum was appended after the Wave 4 provenance fix and built its row
                # by hand, so it silently skipped both provenance fields the other path
                # carries -- 61 of 1,021 rows reached a reviewer with no licence and no
                # attribution at all. One resolver now serves both paths.
                "licence": stated_licence(cat, cat),
                "attribution": cat.get("attribution"),
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
                    "source_name": named_source(r, payload),
                    "source_id": r.get("source_id"),
                    "licence": stated_licence(r, payload),
                    "attribution": payload.get("attribution"),
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
