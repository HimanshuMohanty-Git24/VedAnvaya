#!/usr/bin/env python3
"""Import the validated Samavedic notation. One spec, three modes, nothing else.

WHAT LANDS, AND WHAT DOES NOT.

1,136 ARCIKA_NOTATION rows -> one accented TextVersion witness per verse
    ``text_role = PARALLEL_TEXT``, which the product already maps to the
    ``PARALLEL_WITNESS`` surface and already renders. This is a second WITNESS of a verse's
    own text carrying the Kauthuma numeric svara marks the source printed on it -- not a new
    ontology. ``PRIMARY`` keeps its place at the head of the surface preference, so the
    reader view is unchanged and the notation is offered alongside it.

1,844 SV Mantra nodes -> a typed notation disposition, present AND absent
    Every Samavedic verse gets a state, not only the 1,136 that have notation. A query
    returning nothing but the positive rows lets a reader infer a zero the data never
    stated, and this campaign has already paid for that once. 1,136 read
    ``SOURCE_EXPLICIT_PRESENT``; 708 read ``WITHHELD`` and carry the reason CLASS and the
    reason prose in the row itself.

708 withheld rows -> no notation value, ever
    Including the 39 whose text is released on a coreferent twin. The marks belong to the
    coordinate the witness printed them at; copying a twin's onto another verse because the
    consonants agree would be manufacturing source-explicit data.

0 Gana nodes, 0 MUSICALIZED_AS edges, 0 melodic labels
    ``OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1`` places the object-side Gana model outside
    Product V1, and the 332 GANA_RENDERING rows stay staged. This pass is notation only.

0 pitch, 0 svara names, 0 interpretation
    The marks land as the codepoints the source printed. The Kauthuma decipherment
    authority (van der Hoogt 1929) is not held and Howard 1988 is Jaiminiya.

THE GATE GUARD IS NOT ADVISORY. ``--execute`` refuses unless Gate A is ok, Gate B is PASS
and Gate C is SURVIVED, read out of their artifacts. The owner's clarification is that
"existing validation gates" means all three.

Usage:
    python scripts/samaveda_notation_import.py --plan
    python scripts/samaveda_notation_import.py --execute --backup DIR
    python scripts/samaveda_notation_import.py --readback
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any
from uuid import UUID, uuid5

from neo4j import GraphDatabase, Query, Session

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from vedagraph.domain.tiers import grade_edge

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGING = PROJECT_ROOT / "data" / "staging" / "samaveda_music"
ROWS = STAGING / "rows.jsonl"
REJECTED = STAGING / "rejected.jsonl"
PASS_DIR = PROJECT_ROOT / "data" / "staging" / "samaveda_music_002_final"
OVERLAY = PASS_DIR / "withheld_reason_overlay.json"
GATE_A = PASS_DIR / "gate_a.json"
GATE_B = PROJECT_ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_b.json"
GATE_C = PROJECT_ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_c.json"
PLAN_OUT = PASS_DIR / "migration_plan.json"
RECEIPT = PASS_DIR / "import_receipt.json"
READBACK = PASS_DIR / "readback.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"
TIMEOUT = 600.0

WAVE = "SAMAVEDA_NOTATION_002"

#: The protocol namespace. Changing it would change every entity UUID in the corpus.
VEDAGRAPH_NAMESPACE_UUID = UUID("7c8cde94-2bc0-50e2-8819-568ae65a3ec4")

#: The witness layer's own artifact id. The SV corpus derives a TextVersion's ``text_id``
#: from ``urn:vedagraph:text:{passage_id}:{text_version_id}`` -- verified against the
#: existing PRIMARY_TEXT rows -- so a new ``text_version_id`` yields a fresh, deterministic,
#: collision-free key without touching anything already stored.
TEXT_VERSION_ID = "WIKISOURCE_SA.SV.KAU.ARCIKA_SASVARA"
SOURCE_ARTIFACT_ID = "WIKISOURCE_SA.SV.KAU.SASVARA_PURNA"

#: ``text_id`` is the unique key, and ``text_version_id`` is emphatically NOT: 58,786
#: TextVersion nodes share twelve of them and the largest group is 10,552, so a SET keyed on
#: it would write ten thousand nodes where one was meant. A regression test pins this.
MATCH_KEYS = {"TextVersion": "text_id", "Mantra": "canonical_key"}

NOTATION_PRESENT = "SOURCE_EXPLICIT_PRESENT"
NOTATION_WITHHELD = "WITHHELD"

NOTATION_CONTRACT = (
    "Source-supplied Kauthuma numeric svara notation, released under "
    "OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO and its 2026-09-18 owner clarification that "
    "'existing validation gates' means Gate A, Gate B and Gate C. The marks are recorded as "
    "the codepoints the source printed and are NEVER interpreted into pitch: no decipherment "
    "authority is held. This is notation, not audio -- 0 of 1,844 arcika verses carry "
    "verse-scoped recitation, and no row claims aural verification. The object-side Gana "
    "model is outside Product V1 per OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1, so there is no "
    "saman identity and no MUSICALIZED_AS edge. 1,136 of 1,844 verses carry notation and 708 "
    "are withheld with a typed reason; the coverage is NOT uniform across the collections "
    "(CHANDA 471/585, ARANYA 31/55, MAHANAMNYA 3/10, UTTARA 631/1194) and no Samavedic "
    "figure here may be read as covering the sung Samaveda."
)

WITHHELD_CLASS_BY_NEAR_LINE = {
    True: "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
    False: "NO_NEAR_LINE_PROBABLE_ABSENCE",
}


def derived_uuid(kind: str, *parts: object) -> str:
    component = ":".join(str(part) for part in parts)
    return str(uuid5(VEDAGRAPH_NAMESPACE_UUID, f"urn:vedagraph:{kind}:{component}"))


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


# ---------------------------------------------------------------------------
# The one spec every mode reads
# ---------------------------------------------------------------------------


def build_payload() -> dict[str, Any]:
    """Every write this import will make, built once."""
    notation = [
        r for r in load_jsonl(ROWS) if r["payload"]["layer"] == "ARCIKA_NOTATION"
    ]
    withheld_rows = {
        r["canonical_key"]: r
        for r in load_jsonl(REJECTED)
        if r["disposition"] == "UNRESOLVED" and r["kind"] == "ARCIKA_NOTATION"
    }
    overlay = {}
    if OVERLAY.exists():
        blob = json.loads(OVERLAY.read_text(encoding="utf-8"))
        overlay = {
            c["canonical_key"]: (c["corrected_class"], c["corrected_reason"])
            for c in blob["corrections"]
        }

    witnesses: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []

    for row in notation:
        key = row["canonical_key"]
        payload = row["payload"]
        notated = payload["notated_text_devanagari"]
        witnesses.append(
            {
                "canonical_key": key,
                "text_id": derived_uuid("text", key, TEXT_VERSION_ID),
                "props": {
                    "text_version_id": TEXT_VERSION_ID,
                    "text_role": "PARALLEL_TEXT",
                    "text_form": "SAMHITA",
                    "script": "Devanagari",
                    "language": "sa",
                    "accented": True,
                    "text_nfc": notated,
                    "text_original": notated,
                    "content_sha256": hashlib.sha256(notated.encode("utf-8")).hexdigest(),
                    "rights_status": "CC_BY_SA",
                    "source_id": "WIKISOURCE_SA",
                    "source_artifact_id": SOURCE_ARTIFACT_ID,
                    "source_locator": row["source_locator"],
                    "accent_source": "SOURCE_SUPPLIED_KAUTHUMA_NUMERIC_SVARA",
                    "accent_source_note": (
                        "Combining Devanagari Extended cantillation marks as printed by the "
                        "source. Not inferred, not a font hack, and not the U+0301 acute: "
                        f"{payload['private_use_codepoints']} private-use codepoints and "
                        f"{payload['u0301_combining_acute']} combining acutes on this row."
                    ),
                    "notation_system": payload["notation_system"],
                    "notation_encoding": payload["notation_encoding"],
                    "notation_tone_mark_count": payload["tone_mark_count"],
                    "notation_devanagari_extended_marks": payload[
                        "devanagari_extended_marks"
                    ],
                    "notation_vedic_extensions_marks": payload["vedic_extensions_marks"],
                    "notation_is_interpreted_into_pitch": False,
                    "notation_evidence_layer": row["evidence_layer"],
                    "notation_quality_class": row["quality_class"],
                    "notation_authority_tier": "COMMUNITY_TRANSCRIPTION",
                    "notation_recension": "KAUTHUMA",
                    "notation_recension_verified": row["recension_verified"],
                    "provenance": "SOURCE_EXPLICIT",
                    "provenance_note": NOTATION_CONTRACT,
                    "notation_gates": "A=PASS B=PASS C=SURVIVED",
                    f"{WAVE.lower()}_applied": True,
                },
            }
        )
        dispositions.append(
            {
                "canonical_key": key,
                "props": {
                    "samavedic_notation_state": NOTATION_PRESENT,
                    "samavedic_notation_withheld_class": None,
                    "samavedic_notation_withheld_reason": None,
                    "samavedic_notation_system": payload["notation_system"],
                    "samavedic_notation_source_id": row["source_id"],
                    "samavedic_notation_source_locator": row["source_locator"],
                    "samavedic_notation_tone_mark_count": payload["tone_mark_count"],
                    "samavedic_notation_contract": NOTATION_CONTRACT,
                },
            }
        )

    for key in sorted(withheld_rows):
        row = withheld_rows[key]
        default_class = WITHHELD_CLASS_BY_NEAR_LINE[
            row["nearest_accented_line_similarity_at_least_0_90"]
        ]
        cls, reason = overlay.get(key, (default_class, row["reason"]))
        dispositions.append(
            {
                "canonical_key": key,
                "props": {
                    "samavedic_notation_state": NOTATION_WITHHELD,
                    "samavedic_notation_withheld_class": cls,
                    "samavedic_notation_withheld_reason": reason,
                    "samavedic_notation_system": None,
                    "samavedic_notation_source_id": None,
                    "samavedic_notation_source_locator": None,
                    "samavedic_notation_tone_mark_count": None,
                    "samavedic_notation_contract": NOTATION_CONTRACT,
                },
            }
        )

    # The edge grade comes from the project's single contract, not from this file's opinion
    # and not copied off a neighbouring edge. grade_edge RAISES on a relationship type it has
    # no entry for, which is the behaviour that makes calling it worth more than inlining
    # five strings: if HAS_TEXT_VERSION ever leaves the contract, this import stops.
    grade = grade_edge("HAS_TEXT_VERSION", {}).as_edge_properties()
    edge_properties = {
        **grade,
        # Carried by all 44,276 displayable witness edges and by none of the search
        # derivatives, which is the right split: this is a real text in a real script.
        "language": "sa",
        "text_form": "SAMHITA",
    }

    return {
        "wave": WAVE,
        "witnesses": witnesses,
        "dispositions": dispositions,
        "edge_properties": edge_properties,
        "counts": {
            "text_versions_to_create": len(witnesses),
            "has_text_version_edges_to_create": len(witnesses),
            "mantras_to_type_present": len(witnesses),
            "mantras_to_type_withheld": len(withheld_rows),
            "mantras_to_type_total": len(witnesses) + len(withheld_rows),
            "withheld_by_class": dict(
                collections.Counter(
                    d["props"]["samavedic_notation_withheld_class"]
                    for d in dispositions
                    if d["props"]["samavedic_notation_state"] == NOTATION_WITHHELD
                )
            ),
            "gana_nodes_to_create": 0,
            "musicalized_as_edges_to_create": 0,
            "new_labels_to_create": 0,
            "new_relationship_types_to_create": 0,
            "notation_values_invented": 0,
        },
        "match_keys": MATCH_KEYS,
        "text_id_collisions_within_this_payload": len(witnesses)
        - len({w["text_id"] for w in witnesses}),
    }


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def single(session: Session, query: str, **params: Any) -> Any:
    """One aggregate, or raise.

    ``session.run(...).single()`` returns ``None`` when the query yields no row, and every
    query here is an aggregate that must yield exactly one. Letting the ``None`` through
    would turn a broken query into a figure a reader cannot tell apart from a real zero.
    """
    record = session.run(Query(query, timeout=TIMEOUT), **params).single()
    if record is None:
        raise RuntimeError(f"aggregate returned no row: {query}")
    return record[0]


def census(session: Session) -> dict[str, Any]:
    def scalar(query: str) -> Any:
        return single(session, query)

    return {
        "nodes": scalar("MATCH (n) RETURN count(n)"),
        "relationships": scalar("MATCH ()-[r]->() RETURN count(r)"),
        "TextVersion": scalar("MATCH (n:TextVersion) RETURN count(n)"),
        "HAS_TEXT_VERSION": scalar("MATCH ()-[r:HAS_TEXT_VERSION]->() RETURN count(r)"),
        "SV_mantras": scalar("MATCH (m:Mantra {veda:'SV'}) RETURN count(m)"),
        "SV_text_versions": scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion) RETURN count(t)"
        ),
        "SV_accented_text_versions": scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion) "
            "WHERE t.accented = true RETURN count(t)"
        ),
        "SV_mantras_with_a_notation_state": scalar(
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.samavedic_notation_state IS NOT NULL "
            "RETURN count(m)"
        ),
        "MUSICALIZED_AS": scalar("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)"),
        # The two contracts the first execution missed. Both belong in the census so a
        # later pass sees the gap in the receipt rather than only in the scorecard.
        "TextVersion_without_the_Internal_marker": scalar(
            "MATCH (t:TextVersion) WHERE NOT t:Internal RETURN count(t)"
        ),
        "HAS_TEXT_VERSION_without_a_quality_tier": scalar(
            "MATCH ()-[r:HAS_TEXT_VERSION]->() WHERE r.quality_tier IS NULL RETURN count(r)"
        ),
    }


def fingerprint(session: Session) -> dict[str, Any]:
    labels = {
        r["label"]: r["n"]
        for r in session.run(
            Query(
                "CALL db.labels() YIELD label "
                "CALL (label) { WITH label MATCH (n) WHERE label IN labels(n) "
                "RETURN count(n) AS n } RETURN label, n ORDER BY label",
                timeout=TIMEOUT,
            )
        )
    }
    types = {
        r["t"]: r["n"]
        for r in session.run(
            Query(
                "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY t",
                timeout=TIMEOUT,
            )
        )
    }
    return {
        "labels": labels,
        "relationship_types": types,
        "sha256": hashlib.sha256(
            json.dumps({"labels": labels, "types": types}, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


def take_backup(session: Session, directory: pathlib.Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    counts: dict[str, int] = {}

    nodes = directory / "nodes.jsonl"
    with nodes.open("w", encoding="utf-8", newline="\n") as handle:
        written = 0
        for record in session.run(
            Query(
                "MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props",
                timeout=TIMEOUT,
            )
        ):
            handle.write(
                json.dumps(
                    {"id": record["id"], "labels": record["labels"], "props": record["props"]},
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                + "\n"
            )
            written += 1
    counts["nodes"] = written

    rels = directory / "relationships.jsonl"
    with rels.open("w", encoding="utf-8", newline="\n") as handle:
        written = 0
        for record in session.run(
            Query(
                "MATCH (a)-[r]->(b) RETURN id(r) AS id, type(r) AS type, id(a) AS start, "
                "id(b) AS end, properties(r) AS props",
                timeout=TIMEOUT,
            )
        ):
            handle.write(
                json.dumps(
                    {
                        "id": record["id"],
                        "type": record["type"],
                        "start": record["start"],
                        "end": record["end"],
                        "props": record["props"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                + "\n"
            )
            written += 1
    counts["relationships"] = written

    for path in (nodes, rels):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        digests[path.name] = digest.hexdigest()
        (path.parent / f"{path.name}.sha256").write_text(
            f"{digest.hexdigest()}  {path.name}\n", encoding="utf-8", newline="\n"
        )

    manifest = {
        "artifact": f"{WAVE}_PRE_IMPORT_BACKUP",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "kind": "LOGICAL_EXPORT_NOT_A_BINARY_DUMP",
        "why_not_a_binary_dump": (
            "neo4j-admin database dump needs the database stopped and online backup is an "
            "Enterprise feature. This is the export pattern R3, R4 and R5 each used before "
            "their own mutations: every node and relationship with its internal id and "
            "properties, restorable, no downtime."
        ),
        "counts": counts,
        "sha256": digests,
        "census": census(session),
        "fingerprint": fingerprint(session),
    }
    (directory / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def gates_pass() -> tuple[bool, dict[str, Any]]:
    """Read all three gate artifacts. The owner's clarification is that all three count."""
    state: dict[str, Any] = {}
    ok = True
    for name, path, field, want in (
        ("A", GATE_A, "ok", True),
        ("B", GATE_B, "verdict", "PASS"),
        ("C", GATE_C, "verdict", "SURVIVED"),
    ):
        if not path.exists():
            state[name] = {"present": False}
            ok = False
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        got = blob.get(field)
        state[name] = {
            "present": True,
            "artifact": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "result": "PASS" if (name == "A" and got is True) else got,
            "at": blob.get("at"),
        }
        if got != want:
            ok = False
    state["rule"] = (
        "OWNER-SUPPLIED 2026-09-18: 'existing validation gates' in "
        "OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO means ALL APPLICABLE gates -- A, B and C -- "
        "not Gate A alone. Refusing to execute on anything less is the decision, not caution."
    )
    return ok, state


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def promise(payload: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    """The exact after-census this import commits to, stated before it runs."""
    created = payload["counts"]["text_versions_to_create"]
    return {
        "nodes": before["nodes"] + created,
        "relationships": before["relationships"] + created,
        "TextVersion": before["TextVersion"] + created,
        "HAS_TEXT_VERSION": before["HAS_TEXT_VERSION"] + created,
        "SV_mantras": before["SV_mantras"],
        "SV_text_versions": before["SV_text_versions"] + created,
        "SV_accented_text_versions": before["SV_accented_text_versions"] + created,
        "SV_mantras_with_a_notation_state": payload["counts"]["mantras_to_type_total"],
        "MUSICALIZED_AS": 0,
        "TextVersion_without_the_Internal_marker": 0,
        "HAS_TEXT_VERSION_without_a_quality_tier": 0,
    }


def apply(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """Write the payload. Idempotent, so ``--repair`` can re-run it to close a gap.

    Two things here were missing from the first execution and are the reason ``--repair``
    exists. Both are contracts the rest of the graph already keeps, and both were caught by
    ``scripts/graph_quality_scorecard.py`` reporting exactly 1,136 on three integrity gates
    rather than by anything in this file:

    ``:Internal`` on every TextVersion
        ``TextVersion`` is in ``INTERNAL_LABELS``, and all 58,786 pre-existing ones carry
        the marker. Without it the nodes count as PRODUCT nodes, which made 1,136 of them
        read as leaked internals AND as product nodes with no readable label.

    The five grade properties on every edge
        Taken from ``vedagraph.domain.tiers.grade_edge`` rather than copied off a
        neighbouring edge. This project has already had the attribution axis written by
        three mechanisms that disagreed; the fix was one contract applied last, and an
        unknown relationship type raises rather than defaulting. Calling it here is what
        keeps this import inside that contract instead of beside it.
    """
    created = single(
        session,
        (
            "UNWIND $rows AS row "
            "MATCH (m:Mantra {canonical_key: row.canonical_key}) "
            "MERGE (t:TextVersion {text_id: row.text_id}) "
            "SET t:Internal, t.passage_id = m.entity_id, t += row.props "
            "MERGE (m)-[r:HAS_TEXT_VERSION]->(t) "
            "SET r += $edge "
            "RETURN count(t) AS n"
        ),
        rows=payload["witnesses"],
        edge=payload["edge_properties"],
    )

    typed = single(
        session,
        (
            "UNWIND $rows AS row "
            "MATCH (m:Mantra {canonical_key: row.canonical_key}) "
            "SET m += row.props, m.samavedic_notation_applied_at = $at "
            "RETURN count(m) AS n"
        ),
        rows=payload["dispositions"],
        at=datetime.datetime.now(datetime.UTC).isoformat(),
    )

    return {"text_versions_written": created, "mantras_typed": typed}


def do_readback(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """Re-derive the published claim from the GRAPH, without reading the staging file."""

    def scalar(query: str, **params: Any) -> Any:
        return single(session, query, **params)

    by_collection = {
        r["c"]: r["n"]
        for r in session.run(
            Query(
                "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s}) "
                "RETURN split(m.canonical_key, ':')[3] AS c, count(m) AS n ORDER BY c",
                timeout=TIMEOUT,
            ),
            s=NOTATION_PRESENT,
        )
    }
    denominator = {
        r["c"]: r["n"]
        for r in session.run(
            Query(
                "MATCH (m:Mantra {veda:'SV'}) "
                "RETURN split(m.canonical_key, ':')[3] AS c, count(m) AS n ORDER BY c",
                timeout=TIMEOUT,
            )
        )
    }
    withheld_classes = {
        r["c"]: r["n"]
        for r in session.run(
            Query(
                "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s}) "
                "RETURN m.samavedic_notation_withheld_class AS c, count(m) AS n ORDER BY c",
                timeout=TIMEOUT,
            ),
            s=NOTATION_WITHHELD,
        )
    }

    # The witness text must round-trip: every stored notated string must still hash to what
    # the staging row hashed to. Compared per row rather than as a total, because a total
    # can survive two rows swapping.
    stored = {
        r["k"]: r["h"]
        for r in session.run(
            Query(
                "MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->"
                "(t:TextVersion {text_version_id: $tv}) "
                "RETURN m.canonical_key AS k, t.content_sha256 AS h",
                timeout=TIMEOUT,
            ),
            tv=TEXT_VERSION_ID,
        )
    }
    promised = {w["canonical_key"]: w["props"]["content_sha256"] for w in payload["witnesses"]}
    mismatched = sorted(k for k in promised if stored.get(k) != promised[k])

    return {
        "artifact": f"{WAVE}_READBACK",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "read_from": "the live graph only; the staging rows are used for the hash comparison",
        "notated_verses": scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s}) RETURN count(m)",
            s=NOTATION_PRESENT,
        ),
        "withheld_verses": scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s}) RETURN count(m)",
            s=NOTATION_WITHHELD,
        ),
        "verses_with_no_state_at_all": scalar(
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.samavedic_notation_state IS NULL "
            "RETURN count(m)"
        ),
        "accented_witnesses": scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_version_id: $tv}) WHERE t.accented = true RETURN count(t)",
            tv=TEXT_VERSION_ID,
        ),
        "witnesses_carrying_a_tone_mark": scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_version_id: $tv}) "
            "WHERE t.notation_tone_mark_count > 0 RETURN count(t)",
            tv=TEXT_VERSION_ID,
        ),
        "witnesses_claiming_pitch_interpretation": scalar(
            "MATCH (t:TextVersion {text_version_id: $tv}) "
            "WHERE t.notation_is_interpreted_into_pitch = true RETURN count(t)",
            tv=TEXT_VERSION_ID,
        ),
        "notation_on_a_withheld_verse": scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s})"
            "-[:HAS_TEXT_VERSION]->(t:TextVersion {text_version_id: $tv}) RETURN count(t)",
            s=NOTATION_WITHHELD,
            tv=TEXT_VERSION_ID,
        ),
        "withheld_verses_with_no_reason_class": scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state: $s}) "
            "WHERE m.samavedic_notation_withheld_class IS NULL RETURN count(m)",
            s=NOTATION_WITHHELD,
        ),
        "by_collection": by_collection,
        "denominator_by_collection": denominator,
        "coverage_by_collection": {
            name: round(by_collection.get(name, 0) / total, 4)
            for name, total in sorted(denominator.items())
        },
        "withheld_by_class": withheld_classes,
        "content_hash_mismatches": len(mismatched),
        "content_hash_mismatch_examples": mismatched[:10],
        "musicalized_as_edges": scalar("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)"),
        "gana_labels": single(
            session,
            "CALL db.labels() YIELD label "
            "WHERE label =~ '(?i).*(saman|gana|stobha|melod).*' RETURN collect(label)",
        ),
        "text_versions_sharing_the_new_text_version_id": scalar(
            "MATCH (t:TextVersion {text_version_id: $tv}) RETURN count(t)",
            tv=TEXT_VERSION_ID,
        ),
        "distinct_text_ids_among_them": scalar(
            "MATCH (t:TextVersion {text_version_id: $tv}) RETURN count(DISTINCT t.text_id)",
            tv=TEXT_VERSION_ID,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--readback", action="store_true")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="re-apply the payload idempotently to close a contract gap; creates nothing",
    )
    parser.add_argument("--backup", default="")
    args = parser.parse_args()
    if not (args.plan or args.execute or args.readback or args.repair):
        parser.error("one of --plan, --execute, --repair, --readback")

    payload = build_payload()
    ok, gate_state = gates_pass()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            before = census(session)

            if args.plan or args.execute:
                plan = {
                    "artifact": f"{WAVE}_MIGRATION_PLAN",
                    "at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "head": git("rev-parse", "HEAD"),
                    "gates": gate_state,
                    "gates_pass": ok,
                    "match_keys": payload["match_keys"],
                    "text_version_id": TEXT_VERSION_ID,
                    "text_id_collisions_within_this_payload": payload[
                        "text_id_collisions_within_this_payload"
                    ],
                    "writes": payload["counts"],
                    "census_before": before,
                    "census_promised_after": promise(payload, before),
                    "refuses_to": [
                        "create a Gana node",
                        "create a MUSICALIZED_AS edge",
                        "create any new label or relationship type",
                        "write notation onto a withheld verse",
                        "overwrite the existing SV PRIMARY_TEXT",
                        "interpret a mark into a pitch",
                    ],
                }
                PLAN_OUT.parent.mkdir(parents=True, exist_ok=True)
                PLAN_OUT.write_text(
                    json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                print(f"PLAN  {WAVE}")
                for name, value in payload["counts"].items():
                    print(f"  {name:<42} {value}")
                grades = "/".join(
                    str(gate_state[name]["result"]) for name in ("A", "B", "C")
                )
                print(f"  gates                                      {ok} {grades}")
                print(f"  plan: {PLAN_OUT.relative_to(PROJECT_ROOT)}")

            if args.repair:
                # The payload is the same one --execute used, so this creates nothing: the
                # MERGE finds every node and edge already there and only the SET lands. The
                # assertion is therefore that node and relationship counts do NOT move,
                # which is the opposite promise from --execute and worth stating as such.
                if not ok:
                    print("\n  REFUSED. Gate A, Gate B and Gate C must all pass.")
                    return 1
                applied = apply(session, payload)
                after = census(session)
                repair = {
                    "artifact": f"{WAVE}_REPAIR_RECEIPT",
                    "at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "head": git("rev-parse", "HEAD"),
                    "why": (
                        "The first execution wrote the notation but missed two contracts the "
                        "rest of the graph already keeps: the :Internal marker every one of "
                        "the 58,786 pre-existing TextVersion nodes carries, and the five "
                        "grade properties every HAS_TEXT_VERSION edge carries. Neither was "
                        "caught by this import's own readback -- "
                        "scripts/graph_quality_scorecard.py found them, reporting exactly "
                        "1,136 on internal_leaked, ungraded_edges and nodes_without_label. "
                        "An importer's own success report is not evidence; that is what the "
                        "scorecard is for."
                    ),
                    "grade_source": (
                        "vedagraph.domain.tiers.grade_edge('HAS_TEXT_VERSION'), the "
                        "project's single edge contract, which raises on an uncontracted "
                        "relationship type rather than defaulting"
                    ),
                    "edge_properties_applied": payload["edge_properties"],
                    "applied": applied,
                    "census_after": after,
                    "creates_nothing": {
                        "nodes": before["nodes"] == after["nodes"],
                        "relationships": before["relationships"] == after["relationships"],
                        "nodes_before": before["nodes"],
                        "nodes_after": after["nodes"],
                        "relationships_before": before["relationships"],
                        "relationships_after": after["relationships"],
                    },
                    "contracts_closed": {
                        "TextVersion_without_the_Internal_marker": after[
                            "TextVersion_without_the_Internal_marker"
                        ],
                        "HAS_TEXT_VERSION_without_a_quality_tier": after[
                            "HAS_TEXT_VERSION_without_a_quality_tier"
                        ],
                    },
                }
                (PASS_DIR / "repair_receipt.json").write_text(
                    json.dumps(repair, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                print()
                print(f"REPAIR  {WAVE}")
                print(f"  edge grade                                     {payload['edge_properties']['quality_tier']} / {payload['edge_properties']['knowledge_layer']}")
                print(f"  nodes unchanged                                {repair['creates_nothing']['nodes']}")
                print(f"  relationships unchanged                        {repair['creates_nothing']['relationships']}")
                for name, value in repair["contracts_closed"].items():
                    print(f"  {name:<46} {value}")
                print(f"  receipt: {(PASS_DIR / 'repair_receipt.json').relative_to(PROJECT_ROOT)}")
                return (
                    0
                    if all(repair["creates_nothing"][k] for k in ("nodes", "relationships"))
                    and not any(repair["contracts_closed"].values())
                    else 1
                )

            if not args.execute:
                if args.readback:
                    result = do_readback(session, payload)
                    READBACK.write_text(
                        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                        newline="\n",
                    )
                    print()
                    print(f"READBACK  {WAVE}")
                    for name, value in result.items():
                        if not isinstance(value, (dict, list)):
                            print(f"  {name:<46} {value}")
                    print(f"  readback: {READBACK.relative_to(PROJECT_ROOT)}")
                    return 0
                print("\n  PLAN ONLY. Re-run with --execute --backup <dir>.")
                return 0

            if not ok:
                print("\n  REFUSED. Gate A, Gate B and Gate C must all pass.")
                print(f"  {json.dumps(gate_state, indent=2)}")
                return 1
            if not args.backup:
                print("\n  REFUSED. --execute requires --backup <dir>.")
                return 1

            backup_dir = pathlib.Path(args.backup)
            manifest = take_backup(session, backup_dir)
            print()
            print(f"BACKUP  {backup_dir}")
            print(f"  nodes          {manifest['counts']['nodes']:,}")
            print(f"  relationships  {manifest['counts']['relationships']:,}")
            print(f"  fingerprint    {manifest['fingerprint']['sha256']}")

            promised = promise(payload, before)
            applied = apply(session, payload)
            after = census(session)

            disagreements = {
                name: {"promised": value, "actual": after[name]}
                for name, value in promised.items()
                if after[name] != value
            }
            receipt = {
                "artifact": f"{WAVE}_IMPORT_RECEIPT",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "head": git("rev-parse", "HEAD"),
                "backup": str(backup_dir).replace("\\", "/"),
                "backup_sha256": manifest["sha256"],
                "backup_fingerprint": manifest["fingerprint"]["sha256"],
                "gates": gate_state,
                "applied": applied,
                "census_before": before,
                "census_promised_after": promised,
                "census_actual_after": after,
                "promise_kept": not disagreements,
                "disagreements": disagreements,
                "fingerprint_after": fingerprint(session),
            }
            RECEIPT.write_text(
                json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            print()
            print(f"EXECUTE  {WAVE}")
            for name, value in applied.items():
                print(f"  {name:<46} {value}")
            print(f"  promise kept                                   {not disagreements}")
            if disagreements:
                print(f"  DISAGREEMENTS: {json.dumps(disagreements, indent=2)}")
            print(f"  receipt: {RECEIPT.relative_to(PROJECT_ROOT)}")

            result = do_readback(session, payload)
            READBACK.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            print()
            print(f"READBACK  {WAVE}")
            for name, value in result.items():
                if not isinstance(value, (dict, list)):
                    print(f"  {name:<46} {value}")
            print(f"  readback: {READBACK.relative_to(PROJECT_ROOT)}")
            return 0 if not disagreements else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
